
[app]

title = Car Racing

package.name = carracing

package.domain = org.delltahossein

source.dir = .

source.include_exts = py,png,jpg,jpeg,wav,ogg,ttf,json

version = 1.0

requirements = python3,pygame-ce

orientation = landscape

fullscreen = 1

[buildozer]

log_level = 2

warn_on_root = 1

[app:android]

android.permissions = INTERNET

android.archs = arm64-v8a

android.minapi = 23
