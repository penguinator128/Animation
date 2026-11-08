# Injects the traced logo geometry into the page template -> index.html
g = open('assets/logo-geometry.json').read().strip()
open('index.html', 'w').write(open('src/template.html').read().replace('__GEOM__', g))
