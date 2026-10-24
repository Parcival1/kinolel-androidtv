import java.util.Properties

// KinoLel: Name, Server, Kennung und Version stehen nur in marke.properties
val marke = Properties().apply { rootProject.file("marke.properties").reader(Charsets.UTF_8).use { load(it) } }
fun marke(name: String): String = marke.getProperty(name) ?: error("marke.properties: $name fehlt")

plugins {
	alias(libs.plugins.aboutlibraries)
	alias(libs.plugins.android.application)
	alias(libs.plugins.kotlin.compose)
	alias(libs.plugins.kotlin.serialization)
}

android {
	namespace = "org.jellyfin.androidtv"
	compileSdk = libs.versions.android.compileSdk.get().toInt()

	defaultConfig {
		minSdk = libs.versions.android.minSdk.get().toInt()
		targetSdk = libs.versions.android.targetSdk.get().toInt()

		// KinoLel: eigene Kennung, damit die App neben der KinoLel-Handy-App und der offiziellen Jellyfin-App installierbar ist
		applicationId = marke("APPLICATION_ID")
		versionName = project.getVersionName(fallback = marke("VERSION"))
		versionCode = getVersionCode(versionName!!)

		buildConfigField("String", "KINOLEL_SERVER", "\"${marke("SERVER_URL")}\"")
		buildConfigField("String", "KINOLEL_APPS_LISTE", "\"${marke("APPS_LISTE")}\"")
		buildConfigField("String", "KINOLEL_APPS_SCHLUESSEL", "\"${marke("APPS_SCHLUESSEL")}\"")
		buildConfigField("String", "KINOLEL_UPDATE_REPO", "\"${marke("UPDATE_REPO")}\"")
		buildConfigField("String", "KINOLEL_WUENSCHE", "\"${marke("WUENSCHE_URL")}\"")
		buildConfigField("String", "KINOLEL_WUENSCHE_HU", "\"${marke("WUENSCHE_URL_HU")}\"")
		buildConfigField("String", "KINOLEL_HILFE", "\"${marke("HILFE_URL")}\"")
	}

	// KinoLel: Oberfläche nur Deutsch, Ungarisch und Englisch (Rückfall)
	androidResources {
		localeFilters += listOf("en", "de", "hu")
	}

	buildFeatures {
		buildConfig = true
		viewBinding = true
		compose = true
		resValues = true
	}

	compileOptions {
		isCoreLibraryDesugaringEnabled = true
	}

	signingConfigs {
		val keystoreFile = getProperty("keystore.file")
		val keystorePassword = getProperty("keystore.password")
		val signingKeyAlias = getProperty("signing.key.alias")
		val signingKeyPassword = getProperty("signing.key.password")

		if (keystoreFile != null && keystorePassword != null && signingKeyAlias != null && signingKeyPassword != null) {
			create("release") {
				storeFile = file(keystoreFile)
				storePassword = keystorePassword
				keyAlias = signingKeyAlias
				keyPassword = signingKeyPassword
			}
		}
	}

	dependenciesInfo {
		includeInBundle = false
		includeInApk = false
	}

	buildTypes {
		release {
			isMinifyEnabled = true
			isShrinkResources = true
			proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")

			// Set package names used in various XML files (KinoLel: eigene Kennung statt namespace)
			val id = defaultConfig.applicationId!!
			resValue("string", "app_id", id)
			resValue("string", "app_search_suggest_authority", "${id}.content")
			resValue("string", "app_search_suggest_intent_data", "content://${id}.content/intent")

			// Set flavored application name
			resValue("string", "app_name", marke("APP_NAME"))

			buildConfigField("boolean", "DEVELOPMENT", "false")

			signingConfig = signingConfigs.findByName("release")
		}

		debug {
			// Use different application id to run release and debug at the same time
			applicationIdSuffix = ".debug"

			// Set package names used in various XML files (KinoLel: eigene Kennung statt namespace)
			val id = defaultConfig.applicationId + applicationIdSuffix
			resValue("string", "app_id", id)
			resValue("string", "app_search_suggest_authority", "${id}.content")
			resValue("string", "app_search_suggest_intent_data", "content://${id}.content/intent")

			// Set flavored application name
			resValue("string", "app_name", marke("APP_NAME") + " Test")

			buildConfigField("boolean", "DEVELOPMENT", (defaultConfig.versionCode!! < 100).toString())
		}
	}

	lint {
		lintConfig = file("$rootDir/android-lint.xml")
		abortOnError = false
		checkDependencies = true
	}

	testOptions.unitTests.all {
		it.useJUnitPlatform()
	}
}

base.archivesName.set("kinolel-tv-v${project.getVersionName(fallback = marke("VERSION"))}")

tasks.register("versionTxt") {
	val path = layout.buildDirectory.asFile.get().resolve("version.txt")

	doLast {
		val versionString = "v${android.defaultConfig.versionName}=${android.defaultConfig.versionCode}"
		logger.info("Writing [$versionString] to $path")
		path.writeText("$versionString\n")
	}
}

dependencies {
	// Jellyfin
	implementation(projects.design)
	implementation(projects.playback.core)
	implementation(projects.playback.jellyfin)
	implementation(projects.playback.media3.exoplayer)
	implementation(projects.playback.media3.session)
	implementation(projects.preference)
	implementation(libs.jellyfin.sdk) {
		// Change version if desired
		val sdkVersion = findProperty("sdk.version")?.toString()
		when (sdkVersion) {
			"local" -> version { strictly("latest-SNAPSHOT") }
			"snapshot" -> version { strictly("master-SNAPSHOT") }
			"unstable-snapshot" -> version { strictly("openapi-unstable-SNAPSHOT") }
		}
	}

	// KinoLel: QR-Codes (Quick Connect, Wünsche, Hilfe)
	implementation(libs.zxing.core)

	// Kotlin
	implementation(libs.kotlinx.coroutines)
	implementation(libs.kotlinx.serialization.json)

	// Android(x)
	implementation(libs.androidx.core)
	implementation(libs.androidx.activity)
	implementation(libs.androidx.activity.compose)
	implementation(libs.androidx.fragment)
	implementation(libs.androidx.fragment.compose)
	implementation(libs.androidx.leanback.core)
	implementation(libs.androidx.leanback.preference)
	implementation(libs.androidx.navigation3.ui)
	implementation(libs.androidx.preference)
	implementation(libs.androidx.appcompat)
	implementation(libs.androidx.tvprovider)
	implementation(libs.androidx.constraintlayout)
	implementation(libs.androidx.recyclerview)
	implementation(libs.androidx.work.runtime)
	implementation(libs.bundles.androidx.lifecycle)
	implementation(libs.androidx.window)
	implementation(libs.androidx.cardview)
	implementation(libs.androidx.startup)
	implementation(libs.bundles.androidx.compose)
	implementation(libs.accompanist.permissions)

	// Dependency Injection
	implementation(libs.bundles.koin)

	// Media players
	implementation(libs.androidx.media3.exoplayer)
	implementation(libs.androidx.media3.datasource.okhttp)
	implementation(libs.androidx.media3.exoplayer.hls)
	implementation(libs.androidx.media3.ui)
	implementation(libs.jellyfin.androidx.media3.ffmpeg.decoder)
	implementation(libs.libass.media3)

	// Markdown
	implementation(libs.bundles.markwon)

	// Image utility
	implementation(libs.bundles.coil)

	// Crash Reporting
	implementation(libs.bundles.acra)

	// Licenses
	implementation(libs.aboutlibraries)

	// Logging
	implementation(libs.timber)
	implementation(libs.slf4j.timber)

	// Compatibility (desugaring)
	coreLibraryDesugaring(libs.android.desugar)

	// Testing
	testImplementation(libs.kotest.runner.junit5)
	testImplementation(libs.kotest.assertions)
	testImplementation(libs.mockk)
}
