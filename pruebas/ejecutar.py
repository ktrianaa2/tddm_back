# pruebas/ejecutar.py
import base64
import json
import os
import re
import subprocess
import sys
import tempfile
import shutil
import urllib.request
import urllib.parse
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from pruebas.models import Pruebas
from usuarios.views import validar_token


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS BÁSICOS
# ─────────────────────────────────────────────────────────────────────────────

def _normalizar_prueba(valor):
    if valor is None: return {}
    if isinstance(valor, dict): return valor
    if isinstance(valor, str):
        parsed = valor
        for _ in range(3):
            try:
                parsed = json.loads(parsed)
                if isinstance(parsed, dict): return parsed
            except Exception: return {}
        return {}
    return {}


def _obtener_codigo(prueba_obj):
    detalle = _normalizar_prueba(prueba_obj.prueba)
    codigo = detalle.get('codigo_editado') or detalle.get('codigo_pytest')
    return codigo.strip() if codigo and isinstance(codigo, str) and codigo.strip() else None


def _construir_archivo_pruebas(pruebas_con_codigo):
    lineas = [f"# Generado: {datetime.now().isoformat()}", ""]
    for item in pruebas_con_codigo:
        p = item['prueba']
        lineas.append(f"# ── {p.codigo}: {p.nombre} ──")
        lineas.append(item['codigo'])
        lineas.append("")
    return "\n".join(lineas)


# ─────────────────────────────────────────────────────────────────────────────
# PARSEAR SALIDA DE PYTEST
# ─────────────────────────────────────────────────────────────────────────────

def _parsear_salida(stdout, stderr, returncode):
    salida = stdout + ("\n" + stderr if stderr.strip() else "")
    resultados = []
    pasadas = fallidas = warnings = 0

    for linea in salida.splitlines():
        ls = linea.strip()
        if not ls: continue
        if re.match(r'^[=\-]{5,}', ls):
            resultados.append({'tipo': 'log', 'mensaje': ls}); continue
        m = re.match(r'^(?:.*::)?(test_\w+)\s+(PASSED|FAILED|ERROR|SKIPPED)', ls, re.IGNORECASE)
        if m:
            r = m.group(2).upper()
            if r == 'PASSED':   resultados.append({'tipo': 'success', 'mensaje': f'✓ {ls}'}); pasadas += 1
            elif r in ('FAILED', 'ERROR'): resultados.append({'tipo': 'error', 'mensaje': f'✗ {ls}'}); fallidas += 1
            elif r == 'SKIPPED': resultados.append({'tipo': 'warning', 'mensaje': f'⚠ {ls}'})
            continue
        if re.match(r'^[.FExs]+\s*\[', ls) or re.match(r'^[.FExs]{2,}$', ls):
            resultados.append({'tipo': 'info', 'mensaje': ls}); continue
        if 'warning' in linea.lower():
            resultados.append({'tipo': 'warning', 'mensaje': ls}); warnings += 1; continue
        m2 = re.search(r'(\d+)\s+passed(?:,\s*(\d+)\s+failed)?.*in\s+([\d.]+)s', ls, re.IGNORECASE)
        if m2:
            pasadas = int(m2.group(1) or 0); fallidas = int(m2.group(2) or 0)
            resultados.append({'tipo': 'success' if fallidas == 0 else 'error', 'mensaje': ls}); continue
        if any(kw in linea for kw in ('AssertionError', 'assert ', 'E   ')):
            resultados.append({'tipo': 'error', 'mensaje': ls}); continue
        resultados.append({'tipo': 'log', 'mensaje': ls})

    if not resultados and returncode != 0:
        resultados.append({'tipo': 'error', 'mensaje': f'pytest terminó con código {returncode}.\n{salida[:800]}'})

    return resultados, {'pasadas': pasadas, 'fallidas': fallidas, 'warnings': warnings, 'exitcode': returncode, 'ok': returncode == 0}


# ─────────────────────────────────────────────────────────────────────────────
# AUTO-MOCK — solo para modo sobre_codigo cuando el repo no resuelve todo
# ─────────────────────────────────────────────────────────────────────────────

def _extraer_modulos_faltantes(stdout, stderr):
    salida = stdout + "\n" + stderr
    modulos = set()
    for m in re.finditer(r"No module named '([^']+)'", salida):
        modulos.add(m.group(1).split('.')[0])
    for m in re.finditer(r"cannot import name '[^']+' from '([^']+)'", salida):
        modulos.add(m.group(1).split('.')[0])
    return list(modulos)


def _es_error_solo_de_imports(stdout, stderr, returncode):
    salida = stdout + "\n" + stderr
    tiene_import_error = bool(re.search(r'(ModuleNotFoundError|ImportError|ERROR collecting)', salida))
    tiene_resultados_reales = bool(re.search(r'\s(PASSED|FAILED)\s', salida))
    return tiene_import_error and not tiene_resultados_reales and returncode != 0


_CONFTEST_TEMPLATE = '''
# conftest.py — auto-mock para dependencias externas no disponibles (django, librerías, etc.)
import sys
from unittest.mock import MagicMock

class _MockFinder:
    _raices = set({raices_set})
    def find_module(self, fullname, path=None):
        if fullname.split('.')[0] in self._raices: return self
        return None
    def load_module(self, fullname):
        if fullname in sys.modules: return sys.modules[fullname]
        mock = MagicMock()
        mock.__name__ = fullname; mock.__package__ = fullname.split('.')[0]
        mock.__path__ = []; mock.__spec__ = None
        sys.modules[fullname] = mock
        return mock

if not any(isinstance(f, _MockFinder) for f in sys.meta_path):
    sys.meta_path.insert(0, _MockFinder())
'''


def _generar_conftest_mock(modulos, directorio):
    contenido = _CONFTEST_TEMPLATE.format(
        raices_set=repr(set(m.split('.')[0] for m in modulos))
    )
    with open(os.path.join(directorio, 'conftest.py'), 'w', encoding='utf-8') as f:
        f.write(contenido)


# ─────────────────────────────────────────────────────────────────────────────
# GITHUB: descargar rama al tmpdir
# ─────────────────────────────────────────────────────────────────────────────

_EXT_RELEVANTES = {'py', 'pyi', 'pyx', 'txt', 'cfg', 'ini', 'toml', 'yaml', 'yml', 'json', 'env', 'md', 'rst', 'sh'}
_ARCHIVOS_ESPECIALES = {'requirements', 'requirements.txt', 'setup.py', 'setup.cfg', 'pyproject.toml', 'pytest.ini', 'conftest.py', 'manage.py', '.env', 'Makefile', 'tox.ini'}
_DIRS_IGNORADOS = {'__pycache__', '.git', 'node_modules', 'venv', '.venv', 'env', 'dist', 'build', '.tox', 'migrations'}


def _github_get(url, token):
    req = urllib.request.Request(url)
    req.add_header('Authorization', f'Bearer {token}')
    req.add_header('Accept', 'application/vnd.github+json')
    req.add_header('X-GitHub-Api-Version', '2022-11-28')
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))


def _descargar_repo(token, repo, rama, tmpdir, max_archivos=400):
    advertencias = []
    branch_data = _github_get(f'https://api.github.com/repos/{repo}/branches/{urllib.parse.quote(rama, safe="")}', token)
    tree_sha = branch_data['commit']['commit']['tree']['sha']
    tree_data = _github_get(f'https://api.github.com/repos/{repo}/git/trees/{tree_sha}?recursive=1', token)
    if tree_data.get('truncated'): advertencias.append('⚠️ Repo muy grande — subconjunto de archivos.')

    def _relevante(item):
        if item['type'] != 'blob' or item.get('size', 0) > 500_000: return False
        partes = item['path'].split('/')
        if any(p in _DIRS_IGNORADOS for p in partes[:-1]): return False
        nombre = partes[-1]; ext = nombre.rsplit('.', 1)[-1].lower() if '.' in nombre else ''
        return ext in _EXT_RELEVANTES or nombre in _ARCHIVOS_ESPECIALES

    blobs = [i for i in tree_data.get('tree', []) if _relevante(i)]
    if len(blobs) > max_archivos:
        advertencias.append(f'⚠️ Limitado a {max_archivos} archivos.'); blobs = blobs[:max_archivos]

    descargados = 0
    for item in blobs:
        ruta_rel = item['path']; ruta_dest = os.path.join(tmpdir, ruta_rel)
        os.makedirs(os.path.dirname(ruta_dest), exist_ok=True)
        try:
            blob = _github_get(f'https://api.github.com/repos/{repo}/contents/{urllib.parse.quote(ruta_rel)}?ref={urllib.parse.quote(rama, safe="")}', token)
            contenido = base64.b64decode(blob['content'].replace('\n', '')) if blob.get('encoding') == 'base64' else (blob.get('content') or '').encode('utf-8')
            with open(ruta_dest, 'wb') as f: f.write(contenido)
            descargados += 1
        except Exception as e:
            advertencias.append(f'⚠️ No se descargó {ruta_rel}: {e}')
    return descargados, advertencias


def _detectar_pythonpaths(tmpdir):
    paths = [tmpdir]
    indicadores = {'manage.py', 'setup.py', 'pyproject.toml', 'setup.cfg', 'pytest.ini'}
    for root, dirs, files in os.walk(tmpdir):
        dirs[:] = [d for d in dirs if d not in _DIRS_IGNORADOS]
        if any(f in files for f in indicadores) and root not in paths:
            paths.append(root)
    return paths


# ─────────────────────────────────────────────────────────────────────────────
# EJECUTAR PYTEST
# ─────────────────────────────────────────────────────────────────────────────

def _run_pytest(archivo, cwd, env, timeout):
    proc = subprocess.run(
        [sys.executable, '-m', 'pytest', archivo, '-v', '--tb=short', '--no-header', '-p', 'no:warnings', '--color=no'],
        capture_output=True, text=True, timeout=timeout, cwd=cwd, env=env,
    )
    return proc.stdout, proc.stderr, proc.returncode


# ─────────────────────────────────────────────────────────────────────────────
# MODO 1: PRUEBA SOLA — red phase real, SIN auto-mock
#
# Las pruebas importan desde el proyecto real (from citas.servicios import X).
# Sin el código del proyecto presente, deben fallar con ImportError.
# Eso es exactamente el comportamiento correcto en fase roja de TDD.
# NO se aplica ningún auto-mock — hacerlo falsificaría la fase roja.
# ─────────────────────────────────────────────────────────────────────────────

def _ejecutar_modo_prueba_sola(pruebas_con_codigo, tmpdir, timeout):
    logs = []
    logs.append({'tipo': 'info', 'mensaje': '🔴 MODO: Prueba sola — entorno aislado, sin código del proyecto'})
    logs.append({'tipo': 'info', 'mensaje': '   Las pruebas deben importar desde el proyecto (from modulo import Clase).'})
    logs.append({'tipo': 'info', 'mensaje': '   Lo esperado en TDD es que fallen con ImportError (red phase).'})
    logs.append({'tipo': 'log',  'mensaje': '─' * 50})

    archivo = os.path.join(tmpdir, 'test_generadas.py')
    with open(archivo, 'w', encoding='utf-8') as f:
        f.write(_construir_archivo_pruebas(pruebas_con_codigo))

    # Entorno completamente limpio — sin PYTHONPATH del proyecto
    env = os.environ.copy()
    env.pop('PYTHONPATH', None)

    stdout, stderr, rc = _run_pytest(archivo, tmpdir, env, timeout)
    lineas, resumen = _parsear_salida(stdout, stderr, rc)
    logs.extend(lineas)

    # Interpretación TDD del resultado
    if not resumen['ok']:
        logs.append({'tipo': 'success', 'mensaje': '🔴 Red phase confirmada — las pruebas fallan sin código real.'})
        logs.append({'tipo': 'info',    'mensaje': '   Ahora implementa el código y ejecuta en la pestaña "Sobre código".'})
    else:
        logs.append({'tipo': 'warning', 'mensaje': '⚠️  Las pruebas pasaron sin código del proyecto.'})
        logs.append({'tipo': 'warning', 'mensaje': '   Verifica que el test importe desde el proyecto real (from paquete.modulo import Clase).'})
        logs.append({'tipo': 'warning', 'mensaje': '   Si la clase está definida inline en el test, no es TDD real — usa los prompts actualizados.'})

    return logs, resumen, 'prueba_sola'


# ─────────────────────────────────────────────────────────────────────────────
# MODO 2: SOBRE CÓDIGO — green phase, con repo real + auto-mock solo para
# dependencias externas (django, librerías de terceros, etc.)
#
# Se descarga el repo del proyecto. Los imports del proyecto se resuelven
# con el código real. Solo las librerías externas no instaladas se mockean
# (ej: django, psycopg2) para que pytest pueda correr sin instalar todo.
# ─────────────────────────────────────────────────────────────────────────────

def _ejecutar_modo_sobre_codigo(pruebas_con_codigo, codigo_adicional, tmpdir, timeout, github_token, github_repo, github_rama):
    logs = []
    logs.append({'tipo': 'info', 'mensaje': '🟢 MODO: Sobre código real — con contexto del proyecto'})
    logs.append({'tipo': 'info', 'mensaje': '   Las pruebas se ejecutan contra el código real del proyecto.'})
    logs.append({'tipo': 'info', 'mensaje': '   Lo esperado en TDD es que pasen (green phase).'})
    logs.append({'tipo': 'log',  'mensaje': '─' * 50})

    repo_descargado = False

    if github_token and github_repo and github_rama:
        try:
            n, advertencias = _descargar_repo(github_token, github_repo, github_rama, tmpdir)
            logs.append({'tipo': 'info', 'mensaje': f'📦 Repo cargado: {github_repo} [{github_rama}] — {n} archivo(s)'})
            for adv in advertencias: logs.append({'tipo': 'warning', 'mensaje': adv})
            repo_descargado = True
        except Exception as e:
            logs.append({'tipo': 'error', 'mensaje': f'❌ No se pudo descargar el repo: {e}'})
            logs.append({'tipo': 'warning', 'mensaje': 'Continuando sin contexto de repo — los imports del proyecto fallarán.'})

    # Archivo de pruebas en subcarpeta separada
    tests_dir = os.path.join(tmpdir, '_tddm_tests')
    os.makedirs(tests_dir, exist_ok=True)
    archivo = os.path.join(tests_dir, 'test_generadas.py')

    contenido = _construir_archivo_pruebas(pruebas_con_codigo)
    if not repo_descargado and codigo_adicional:
        contenido = "# ── Código del proyecto (manual) ──\n" + codigo_adicional + "\n\n# ── Pruebas ──\n" + contenido

    with open(archivo, 'w', encoding='utf-8') as f:
        f.write(contenido)

    # conftest raíz para que pytest encuentre el proyecto
    raiz_conftest = os.path.join(tmpdir, 'conftest.py')
    if not os.path.exists(raiz_conftest):
        with open(raiz_conftest, 'w') as f: f.write('# conftest raíz\n')

    env = os.environ.copy()
    if repo_descargado:
        paths = _detectar_pythonpaths(tmpdir)
        sep = ';' if sys.platform == 'win32' else ':'
        env['PYTHONPATH'] = sep.join(paths)

    # Intento 1: con código real
    stdout, stderr, rc = _run_pytest(archivo, tmpdir, env, timeout)

    # Si solo fallan dependencias externas (django, librerías), mockear SOLO esas
    # y reintentar. Los módulos del proyecto NO se mockean — si fallan, el código
    # del proyecto tiene un problema real.
    mock_usados = []
    intentos = 0
    while _es_error_solo_de_imports(stdout, stderr, rc) and intentos < 3:
        todos_faltantes = _extraer_modulos_faltantes(stdout, stderr)

        # Separar: módulos del proyecto (deben existir en el repo) vs externos
        modulos_proyecto = _inferir_modulos_proyecto(github_repo)
        externos = [m for m in todos_faltantes if m not in modulos_proyecto and m not in mock_usados]
        del_proyecto = [m for m in todos_faltantes if m in modulos_proyecto]

        if del_proyecto:
            # Un módulo del proyecto falta → el código no está implementado
            logs.append({'tipo': 'error', 'mensaje': f'❌ Módulos del proyecto no encontrados: {", ".join(del_proyecto)}'})
            logs.append({'tipo': 'error', 'mensaje': '   El código del proyecto no tiene esos módulos implementados aún.'})
            logs.append({'tipo': 'info',  'mensaje': '   Implementa el código y vuelve a ejecutar.'})
            break

        if not externos:
            break

        mock_usados.extend(externos)
        logs.append({'tipo': 'info', 'mensaje': f'🔧 Mockeando dependencias externas: {", ".join(externos)}'})
        _generar_conftest_mock(mock_usados, tests_dir)
        stdout, stderr, rc = _run_pytest(archivo, tmpdir, env, timeout)
        intentos += 1

    lineas, resumen = _parsear_salida(stdout, stderr, rc)
    logs.extend(lineas)

    if mock_usados:
        logs.append({'tipo': 'info', 'mensaje': f'ℹ️  Dependencias externas mockeadas (no del proyecto): {", ".join(mock_usados)}'})

    # Interpretación TDD
    if resumen['ok']:
        logs.append({'tipo': 'success', 'mensaje': '🟢 Green phase — el código cumple lo que especifican las pruebas.'})
    else:
        logs.append({'tipo': 'error', 'mensaje': '❌ Las pruebas fallan contra el código real — el código no cumple el contrato.'})
        logs.append({'tipo': 'info',  'mensaje': '   Revisa la implementación en el repo y vuelve a ejecutar.'})

    modo = 'sobre_codigo_real' if repo_descargado else 'sobre_codigo_manual'
    return logs, resumen, modo


def _inferir_modulos_proyecto(github_repo):
    """
    Infiere los nombres de módulo que pertenecen al proyecto basándose en
    el nombre del repo. Si el repo se llama 'usuario/mi_proyecto_back',
    los módulos 'mi_proyecto', 'citas', 'pacientes', etc. son del proyecto.
    Esta es una heurística simple — el backend puede mejorarla inspeccionando
    el árbol descargado en tmpdir.
    """
    if not github_repo:
        return set()
    # Tomar la parte después del '/' y quitar sufijos comunes
    nombre = github_repo.split('/')[-1].lower()
    for sufijo in ['_back', '_backend', '_api', '_server', '_app']:
        nombre = nombre.replace(sufijo, '')
    return {nombre.replace('-', '_')}


# ─────────────────────────────────────────────────────────────────────────────
# VISTA PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def ejecutar_pruebas(request):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido o requerido'}, status=401)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido en el body'}, status=400)

    prueba_ids       = body.get('prueba_ids', [])
    codigo_adicional = body.get('codigo_adicional', '').strip()
    timeout          = min(int(body.get('timeout', 120)), 300)
    modo_ejecucion   = body.get('modo_ejecucion', 'prueba_sola')  # 'prueba_sola' | 'sobre_codigo'
    # sin_mock=True viene del frontend en modo prueba_sola (doble seguridad)
    sin_mock         = body.get('sin_mock', False)

    github_token = body.get('github_token', '').strip()
    github_repo  = body.get('github_repo', '').strip()
    github_rama  = body.get('github_rama', '').strip()

    if not prueba_ids or not isinstance(prueba_ids, list):
        return JsonResponse({'error': 'prueba_ids es requerido y debe ser una lista'}, status=400)

    pruebas_db = list(Pruebas.objects.filter(id__in=prueba_ids, activo=True, estado='Aprobada').select_related('tipo_prueba'))
    if not pruebas_db:
        return JsonResponse({'error': 'No se encontraron pruebas aprobadas con esos IDs'}, status=404)

    pruebas_con_codigo, pruebas_sin_codigo = [], []
    for p in pruebas_db:
        codigo = _obtener_codigo(p)
        if codigo: pruebas_con_codigo.append({'prueba': p, 'codigo': codigo})
        else: pruebas_sin_codigo.append({'id': p.id, 'codigo': p.codigo, 'nombre': p.nombre})

    if not pruebas_con_codigo:
        return JsonResponse({
            'ok': False, 'error': 'Ninguna prueba tiene código pytest generado',
            'pruebas_sin_codigo': pruebas_sin_codigo,
            'resultados': [{'tipo': 'warning', 'mensaje': '⚠️ No hay código pytest. Regenera las pruebas con IA.'}],
            'resumen': {'pasadas': 0, 'fallidas': 0, 'warnings': 1, 'exitcode': -1, 'ok': False},
        }, status=200)

    inicio = datetime.now()
    tmpdir = None

    try:
        tmpdir = tempfile.mkdtemp(prefix='tddm_pytest_')

        if modo_ejecucion == 'sobre_codigo' and not sin_mock:
            logs, resumen, modo = _ejecutar_modo_sobre_codigo(
                pruebas_con_codigo, codigo_adicional,
                tmpdir, timeout,
                github_token, github_repo, github_rama,
            )
        else:
            # prueba_sola O sin_mock=True → red phase real, sin auto-mock
            logs, resumen, modo = _ejecutar_modo_prueba_sola(
                pruebas_con_codigo, tmpdir, timeout,
            )

        tiempo = (datetime.now() - inicio).total_seconds()

        if pruebas_sin_codigo:
            logs.append({'tipo': 'warning', 'mensaje': f'⚠️ {len(pruebas_sin_codigo)} prueba(s) sin código omitidas: ' + ', '.join(p["codigo"] for p in pruebas_sin_codigo)})

        return JsonResponse({
            'ok': resumen['ok'], 'resultados': logs, 'resumen': resumen,
            'pruebas_ejecutadas': [{'id': i['prueba'].id, 'codigo': i['prueba'].codigo, 'nombre': i['prueba'].nombre} for i in pruebas_con_codigo],
            'pruebas_sin_codigo': pruebas_sin_codigo,
            'tiempo_ejecucion': f'{tiempo:.2f}s', 'modo': modo, 'error': None,
        }, status=200)

    except subprocess.TimeoutExpired:
        tiempo = (datetime.now() - inicio).total_seconds()
        return JsonResponse({'ok': False, 'resultados': [{'tipo': 'error', 'mensaje': f'⏱️ Timeout tras {timeout}s'}], 'resumen': {'pasadas': 0, 'fallidas': len(pruebas_con_codigo), 'warnings': 0, 'exitcode': -1, 'ok': False}, 'pruebas_ejecutadas': [], 'pruebas_sin_codigo': pruebas_sin_codigo, 'tiempo_ejecucion': f'{tiempo:.2f}s', 'modo': modo_ejecucion, 'error': f'Timeout {timeout}s'}, status=200)

    except Exception as e:
        import traceback; traceback.print_exc()
        return JsonResponse({'ok': False, 'error': str(e), 'resultados': [{'tipo': 'error', 'mensaje': f'💥 {str(e)}'}], 'resumen': {'pasadas': 0, 'fallidas': 0, 'warnings': 0, 'exitcode': -1, 'ok': False}, 'pruebas_ejecutadas': [], 'pruebas_sin_codigo': pruebas_sin_codigo if 'pruebas_sin_codigo' in dir() else [], 'tiempo_ejecucion': '0s', 'modo': modo_ejecucion}, status=500)

    finally:
        if tmpdir and os.path.exists(tmpdir):
            shutil.rmtree(tmpdir, ignore_errors=True)