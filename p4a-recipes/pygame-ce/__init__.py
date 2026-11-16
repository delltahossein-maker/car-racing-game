
from pythonforandroid.recipe import (
    CompiledComponentsPythonRecipe
)
from pythonforandroid.toolchain import current_directory


class PygameCeRecipe(CompiledComponentsPythonRecipe):

    version = "2.5.0"

    url = (
        "https://github.com/pygame-community/"
        "pygame-ce/archive/refs/tags/{version}.tar.gz"
    )

    name = "pygame-ce"
    site_packages_name = "pygame-ce"

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

    def prebuild_arch(self, arch):
        super().prebuild_arch(arch)

        with current_directory(self.get_build_dir(arch.arch)):
            pass


recipe = PygameCeRecipe()


