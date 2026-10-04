""" Mode names used by the apps that follow the MODE_CHANGE convention.

    Uses the translations from Lightwand (https://github.com/Pythm/ad-Lightwand)
    when it is installed, so your own mode names are used. Without Lightwand
    the default English names are used and nothing else is needed.

    Use in an app:  from mode_names import translations

    @Pythm / https://github.com/Pythm
"""

__version__ = "0.1.0"

try:
    from translations_lightmodes import translations
except ImportError:
    class _EnglishModes:
        MODE_CHANGE = 'MODE_CHANGE'
        automagical = 'automagical'
        morning = 'morning'
        night = 'night'
        away = 'away'
        off = 'off'
        custom = 'custom'
        fire = 'fire'
        false_alarm = 'false-alarm'
        wash = 'wash'
        reset = 'reset'
        language = 'en'

    translations = _EnglishModes()
