package com.sattrack.data.repository

import android.content.Context
import android.content.SharedPreferences
import com.sattrack.data.model.ObserverLocation

class UserPreferencesRepository(context: Context) {

    private val prefs: SharedPreferences =
        context.getSharedPreferences("sattrack_native_prefs", Context.MODE_PRIVATE)

    var aiProvider: String
        get() = prefs.getString("ai_provider", "local") ?: "local"
        set(value) = prefs.edit().putString("ai_provider", value).apply()

    var aiApiKey: String
        get() = prefs.getString("ai_api_key", "") ?: ""
        set(value) = prefs.edit().putString("ai_api_key", value).apply()

    var observerLocation: ObserverLocation
        get() {
            val lat = prefs.getFloat("obs_lat", 37.7749f).toDouble()
            val lng = prefs.getFloat("obs_lng", -122.4194f).toDouble()
            val name = prefs.getString("obs_name", "Observer Location") ?: "Observer Location"
            return ObserverLocation(latDeg = lat, lngDeg = lng, name = name)
        }
        set(value) {
            prefs.edit()
                .putFloat("obs_lat", value.latDeg.toFloat())
                .putFloat("obs_lng", value.lngDeg.toFloat())
                .putString("obs_name", value.name)
                .apply()
        }

    var useMetric: Boolean
        get() = prefs.getBoolean("use_metric", true)
        set(value) = prefs.edit().putBoolean("use_metric", value).apply()
}
