import caty.template.smarty
import caty.template.smartymx
import caty.template.genshi
compilers = {
    'smarty': smartymx.SmartyMXCompiler(),
    'smarty-mx': smartymx.SmartyMXCompiler(),
    'genshi': genshi.build_compiler(),
}
