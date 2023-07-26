# rift wizard patcher by anotak

# put DONT_PATCH_MY_STAR_IMPORTS at the top of your file to exclude it from
# patching
DONT_PATCH_MY_STAR_IMPORTS = True

# if you want to use this in your own mod, just copy the file into a folder
# in your mod and import that version. the reason is that the list of modules
# is built when this is loaded, so each instance of Patcher.py should only
# be affecting the stuff in mods loaded before it

import sys
sys.path.append('../..')

exclude_set = {'_frozen_importlib','_frozen_importlib_external','codecs','encodings.aliases','encodings','encodings.utf_8','encodings.cp1252','__main__','encodings.latin_1','abc','io','struct','pyimod01_os_path','pyimod02_archive','pyimod03_importers','stat','_collections_abc','genericpath','ntpath','os.path','os','_ctypes','ctypes._endian','ctypes','__future__','types','enum','sre_constants','sre_parse','sre_compile','operator','keyword','heapq','reprlib','collections','functools','copyreg','re','importlib._bootstrap','importlib._bootstrap_external','warnings','importlib','importlib.machinery','importlib.abc','contextlib','importlib.util','posixpath','fnmatch','_compression','_weakrefset','threading','_bz2','bz2','_lzma','lzma','shutil','zipfile','weakref','pkgutil','platform','datetime','xml','xml.parsers','pyexpat','xml.parsers.expat','plistlib','email','email.errors','string','email.quoprimime','base64','email.base64mime','quopri','email.encoders','email.charset','email.header','bisect','random','_socket','collections.abc','select','selectors','socket','urllib','urllib.parse','locale','calendar','email._parseaddr','email.utils','email._policybase','email.feedparser','email.parser','tempfile','textwrap','opcode','dis','token','tokenize','linecache','inspect','pkg_resources.extern','pkg_resources._vendor','pkg_resources.extern.six','pkg_resources._vendor.six','pkg_resources.py31compat','pkg_resources.extern.appdirs','pkg_resources._vendor.packaging.__about__','pkg_resources.extern.packaging','pkg_resources.extern.packaging._structures','pkg_resources.extern.packaging.version','pkg_resources.extern.packaging._compat','pkg_resources.extern.packaging.specifiers','copy','pprint','traceback','pkg_resources.extern.pyparsing','pkg_resources.extern.packaging.markers','pkg_resources.extern.packaging.requirements','sysconfig','pkg_resources','signal','multiprocessing.process','_compat_pickle','pickle','multiprocessing.reduction','multiprocessing.context','__mp_main__','multiprocessing','runpy','subprocess','multiprocessing.util','multiprocessing.spawn','multiprocessing.popen_spawn_win32','pygame.base','pygame.constants','pygame.version','pygame.rect','pygame.compat','pygame.rwobject','pygame.surflock','pygame.colordict','pygame.color','pygame.bufferproxy','pygame.math','pygame.surface','pygame.display','pygame.draw','pygame.event','pygame.imageext','pygame.image','pygame.joystick','pygame.key','pygame.mouse','pygame.cursors','pygame.time','pygame.mask','pygame.sprite','_queue','queue','pygame.threads','pygame.pixelcopy','pygame.pixelarray','pygame.transform','pygame.font','pygame.sysfont','pygame.mixer_music','pygame.mixer','pygame.scrap','numpy._globals','numpy.__config__','numpy.version','glob','numpy._distributor_init','numpy.core._multiarray_umath','numpy.compat._inspect','pathlib','numpy.compat.py3k','numpy.compat','numpy.core.overrides','numpy.core.multiarray','numpy.core.umath','numbers','numpy.core._string_helpers','numpy.core._dtype','numpy.core._type_aliases','numpy.core.numerictypes','numpy.core._asarray','numpy.core._exceptions','numpy.core._methods','numpy.core.fromnumeric','numpy.core.shape_base','numpy.core._ufunc_config','numpy.core.arrayprint','numpy.core.numeric','numpy.core.defchararray','numpy.core.records','numpy.core.memmap','numpy.core.function_base','numpy.core.machar','numpy.core.getlimits','numpy.core.einsumfunc','numpy.core._multiarray_tests','numpy.core._add_newdocs','numpy.core._dtype_ctypes','ast','numpy.core._internal','numpy._pytesttester','numpy.core','numpy.lib.mixins','numpy.lib.ufunclike','numpy.lib.type_check','numpy.lib.scimath','numpy.lib.twodim_base','numpy.linalg.lapack_lite','numpy.linalg._umath_linalg','numpy.linalg.linalg','numpy.linalg','numpy.matrixlib.defmatrix','numpy.matrixlib','numpy.lib.histograms','numpy.lib.function_base','numpy.lib.stride_tricks','numpy.lib.index_tricks','numpy.lib.nanfunctions','numpy.lib.shape_base','numpy.lib.polynomial','numpy.lib.utils','numpy.lib.arraysetops','numpy.lib.format','numpy.lib._datasource','numpy.lib._iotools','numpy.lib.npyio','_decimal','decimal','numpy.lib.financial','numpy.lib.arrayterator','numpy.lib.arraypad','numpy.lib._version','numpy.lib','numpy.fft._pocketfft_internal','numpy.fft._pocketfft','numpy.fft.helper','numpy.fft','numpy.polynomial.polyutils','numpy.polynomial._polybase','numpy.polynomial.polynomial','numpy.polynomial.chebyshev','numpy.polynomial.legendre','numpy.polynomial.hermite','numpy.polynomial.hermite_e','numpy.polynomial.laguerre','numpy.polynomial','numpy.random._common','_hashlib','hashlib','hmac','secrets','numpy.random.bit_generator','numpy.random._bounded_integers','numpy.random._mt19937','numpy.random.mtrand','numpy.random._philox','numpy.random._pcg64','numpy.random._sfc64','numpy.random._generator','numpy.random._pickle','numpy.random','numpy.ctypeslib','numpy.ma.core','numpy.ma.extras','numpy.ma','numpy','pygame.surfarray','pygame.sndarray','pygame.fastevent','pygame','pygame.locals','logging','cffi.lock','cffi.error','cffi.model','cffi.api','cffi','typing','_cffi_backend','cffi.commontypes','pycparser.ply','pycparser.ply.yacc','pycparser.c_ast','pycparser.ply.lex','pycparser.c_lexer','pycparser.plyparser','pycparser.ast_transforms','pycparser.c_parser','pycparser','cffi.cparser','pycparser.lextab','pycparser.yacctab','tcod._libtcod','tcod.loader','tcod._internal','tcod.color','tcod.constants','tcod.random','tcod.bsp','tcod.console','tcod.image','tcod.map','tcod.noise','tcod.path','tcod.libtcodpy','tcod.version','tcod','_bootlocale','dill.info','_pyio','dill.settings','dill._dill','dill.source','dill.temp','dill.pointers','dill.detect','dill.objtypes','dill','steamworks.enums','steamworks.util','steamworks.structs','steamworks.exceptions','steamworks.methods','steamworks.interfaces','steamworks.interfaces.apps','steamworks.interfaces.friends','steamworks.interfaces.matchmaking','steamworks.interfaces.music','steamworks.interfaces.screenshots','steamworks.interfaces.users','steamworks.interfaces.userstats','steamworks.interfaces.utils','steamworks.interfaces.workshop','steamworks'}

DEBUG_PATCHERS = False
if 'debug_patchers' in sys.argv:
    DEBUG_PATCHERS = True
    
    print(__name__ + ": patcher version 1")

def build_to_replace_modules():
    global DEBUG_PATCHERS
    
    to_replace_modules = []
    modules = sys.modules.copy()
    
    for key in modules:
        mod = modules[key]
        
        if key in exclude_set:
            continue
        
        # the modules that don't have __file__ are like builtin stuff
        if hasattr(mod,'__file__'):
            filename = mod.__file__
            
            # modules can opt out of having their imports replaced setting a
            # DONT_PATCH_MY_STAR_IMPORTS = True at the top
            if hasattr(mod,'DONT_PATCH_MY_STAR_IMPORTS') and getattr(mod,'DONT_PATCH_MY_STAR_IMPORTS'):
                if DEBUG_PATCHERS:
                    print(__name__ + ": EXCLUDING " + key)
                
                break
            
            if DEBUG_PATCHERS:
                print(__name__ + ": will patch " + key)
            
            to_replace_modules.append(mod)
    
    return to_replace_modules

to_replace_modules = build_to_replace_modules()


# replaces vanilla code without overwriting other mods' code
def replace_only_vanilla_code(original_function, replacing_function):
    import inspect
    
    path = inspect.getsourcefile( original_function )
    
    if "mods\\" in path or "mods/" in path:
        return False
    
    patch_general(original_function, replacing_function)
    
    return True

# same but if the code is in a list
def replace_only_vanilla_code_in_list(original_function, replacing_function, list):
    import inspect
    
    path = inspect.getsourcefile( original_function )
    
    if "mods\\" in path or "mods/" in path:
        return False
    
    replaced = True
    while replaced:
        replaced = False
        current = 0
        found = -1
        for _ in list:
            if _ == original_function:
                found = current
                replaced = True
                break
            
            current += 1
        
        list[found] = replacing_function

# credit to ceph3us for this function, thank you
def patch_general(obj, replacement):
    parts = obj.__qualname__.split('.')
    root_global, path, name = parts[0], parts[1:-1], parts[-1]
    target = obj.__globals__[root_global]
    for attr in path:
        target = getattr(target, attr)
    setattr(target, name, replacement)
    
    # anotak - okay this part after here is me not ceph3us
    if name.startswith('__'):
        # seems like a bad idea to replace stuff like __init__ here so let's not do that
        return
    
    # replacing everything in 
    for mod in to_replace_modules:
        if hasattr(mod,name):
            attr = getattr(mod,name)
            if attr == obj:
                target = setattr(mod, name, replacement)


# if you need to do performance testing, usage is like:
# some_function = profile_function(original_function)
# replace_only_vanilla_code(original_function, some_function)
def profile_function(original_function, percent=0.5):
    def profiled_function(self, *args, **kwargs):
        import time
        import cProfile
        import pstats

        pr = cProfile.Profile()
        start = time.perf_counter()
        pr.enable()
        
        output = original_function(self, *args, **kwargs)
        
        pr.disable()

        finish = time.perf_counter()
        total_time = finish - start

        print("function ms: %f" % (total_time * 1000))
        stats = pstats.Stats(pr)
        stats.sort_stats("cumtime")
        stats.dump_stats("draw_profile.stats")
        stats.print_stats(percent)
        
        return output
    
    patch_general(original_function, profiled_function)
    
    return profiled_function