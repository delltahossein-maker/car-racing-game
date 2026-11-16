
from os.path import join

from pythonforandroid.recipe import CompiledComponentsPythonRecipe


class PygameCERecipe(CompiledComponentsPythonRecipe):

    version = "2.5.0"

    url = (
        "https://github.com/pygame-community/"
        "pygame-ce/archive/refs/tags/{version}.tar.gz"
    )

    site_packages_name = "pygame-ce"
    name = "pygame-ce"

    depends = [
        "sdl2",
        "sdl2_image",
        "sdl2_mixer",
        "sdl2_ttf",
        "setuptools",
        "jpeg",
        "png",
    ]

    call_hostpython_via_targetpython = False
    install_in_hostpython = False


recipe = PygameCERecipe()

