
class Localization:
    translation = {
        'none': {

        },
        'ru': {

        },
        'en': {

        },
        'uz': {

        }
    }

    @staticmethod
    def get_translation(language, key):
        return Localization.translation.get(language, {}).get(key, key)


async def get_localized_message(language, key):
    translation = Localization.get_translation(language, key)
    return translation
