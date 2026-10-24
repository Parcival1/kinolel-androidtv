package org.jellyfin.androidtv.preference

import org.jellyfin.androidtv.constant.HomeSectionType
import org.jellyfin.androidtv.preference.store.DisplayPreferencesStore
import org.jellyfin.preference.enumPreference
import org.jellyfin.preference.intPreference
import org.jellyfin.sdk.api.client.ApiClient

class UserSettingPreferences(
	api: ApiClient,
) : DisplayPreferencesStore(
	displayPreferencesId = "usersettings",
	api = api,
	app = "emby",
) {
	companion object {
		val skipBackLength = intPreference("skipBackLength", 10_000)
		val skipForwardLength = intPreference("skipForwardLength", 30_000)

		// KinoLel: Startseite wie im Web – „Weiter ansehen“ und „Als Nächstes“ getrennt, dann „Zuletzt hinzugefügt“
		// je Bibliothek, dann die Bibliotheksübersicht (Live-TV, Musik und Bücher gibt es bei KinoLel nicht)
		val homesection0 = enumPreference("homesection0", HomeSectionType.RESUME)
		val homesection1 = enumPreference("homesection1", HomeSectionType.NEXT_UP)
		val homesection2 = enumPreference("homesection2", HomeSectionType.LATEST_MEDIA)
		val homesection3 = enumPreference("homesection3", HomeSectionType.LIBRARY_TILES_SMALL)
		val homesection4 = enumPreference("homesection4", HomeSectionType.NONE)
		val homesection5 = enumPreference("homesection5", HomeSectionType.NONE)
		val homesection6 = enumPreference("homesection6", HomeSectionType.NONE)
		val homesection7 = enumPreference("homesection7", HomeSectionType.NONE)
		val homesection8 = enumPreference("homesection8", HomeSectionType.NONE)
		val homesection9 = enumPreference("homesection9", HomeSectionType.NONE)
	}

	val homesections = listOf(
		homesection0,
		homesection1,
		homesection2,
		homesection3,
		homesection4,
		homesection5,
		homesection6,
		homesection7,
		homesection8,
		homesection9,
	)

	val activeHomesections
		get() = homesections
			.map(::get)
			.filterNot { it == HomeSectionType.NONE }
}
