package com.sattrack.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import com.sattrack.data.model.ObserverLocation
import com.sattrack.data.model.SatelliteState
import com.sattrack.ui.theme.*
import kotlin.math.cos
import kotlin.math.sin

@Composable
fun OrbitMapView(
    satellites: List<SatelliteState>,
    selectedId: Int,
    observer: ObserverLocation,
    onSelectSatellite: (Int) -> Unit,
    modifier: Modifier = Modifier
) {
    Canvas(
        modifier = modifier
            .fillMaxSize()
            .pointerInput(satellites) {
                detectTapGestures { tapOffset ->
                    val w = size.width
                    val h = size.height

                    // Check if tapped near any satellite
                    satellites.forEach { sat ->
                        val satX = ((sat.lngDeg + 180.0) / 360.0 * w).toFloat()
                        val satY = ((90.0 - sat.latDeg) / 180.0 * h).toFloat()
                        val dist = (tapOffset.x - satX) * (tapOffset.x - satX) + (tapOffset.y - satY) * (tapOffset.y - satY)
                        if (dist < 40f * 40f) {
                            onSelectSatellite(sat.id)
                        }
                    }
                }
            }
    ) {
        val w = size.width
        val h = size.height

        // 1. Cyber Dark Map Background
        drawRect(color = BgVoid)

        // 2. Map Graticules (Latitude & Longitude lines)
        val gridColor = Color(0x1F38BDF8)
        for (lon in -180..180 step 45) {
            val x = ((lon + 180.0) / 360.0 * w).toFloat()
            drawLine(color = gridColor, start = Offset(x, 0f), end = Offset(x, h), strokeWidth = 1f)
        }
        for (lat in -60..60 step 30) {
            val y = ((90.0 - lat) / 180.0 * h).toFloat()
            drawLine(color = gridColor, start = Offset(0f, y), end = Offset(w, y), strokeWidth = 1f)
        }

        // Equator Highlight
        val equatorY = h / 2f
        drawLine(color = Color(0x3D38BDF8), start = Offset(0f, equatorY), end = Offset(w, equatorY), strokeWidth = 2f)

        // 3. Day/Night Solar Terminator Wave
        val now = System.currentTimeMillis()
        val gmtHours = (now % 86400000L) / 3600000.0
        val subsolarLng = (12.0 - gmtHours) * 15.0

        val terminatorPath = Path()
        var first = true
        for (lonDeg in -180..180 step 5) {
            val deltaRad = Math.toRadians(lonDeg - subsolarLng)
            val decRad = Math.toRadians(-23.44 * cos(2.0 * Math.PI * (now / 86400000.0 + 10.0) / 365.25))
            val latRad = -kotlin.math.atan(cos(deltaRad) / kotlin.math.tan(decRad))
            val latDeg = Math.toDegrees(latRad).coerceIn(-80.0, 80.0)

            val x = ((lonDeg + 180.0) / 360.0 * w).toFloat()
            val y = ((90.0 - latDeg) / 180.0 * h).toFloat()

            if (first) {
                terminatorPath.moveTo(x, y)
                first = false
            } else {
                terminatorPath.lineTo(x, y)
            }
        }
        drawPath(path = terminatorPath, color = AmberAccent.copy(alpha = 0.45f), style = Stroke(width = 2f))

        // 4. Observer Location Marker
        val obsX = ((observer.lngDeg + 180.0) / 360.0 * w).toFloat()
        val obsY = ((90.0 - observer.latDeg) / 180.0 * h).toFloat()
        drawCircle(color = EmeraldAccent.copy(alpha = 0.25f), radius = 24f, center = Offset(obsX, obsY))
        drawCircle(color = EmeraldAccent, radius = 6f, center = Offset(obsX, obsY))

        // 5. Satellites: Footprints & Markers
        satellites.forEach { sat ->
            val isSelected = sat.id == selectedId
            val satX = ((sat.lngDeg + 180.0) / 360.0 * w).toFloat()
            val satY = ((90.0 - sat.latDeg) / 180.0 * h).toFloat()

            val satColor = try {
                Color(android.graphics.Color.parseColor(sat.colorHex))
            } catch (_: Exception) {
                CyanAccent
            }

            // Footprint circle
            val fpRadiusPx = (sat.footprintKm / 40075.0 * w).toFloat().coerceIn(20f, 180f)
            drawCircle(
                color = satColor.copy(alpha = if (isSelected) 0.12f else 0.06f),
                radius = fpRadiusPx,
                center = Offset(satX, satY)
            )
            drawCircle(
                color = satColor.copy(alpha = if (isSelected) 0.7f else 0.35f),
                radius = fpRadiusPx,
                center = Offset(satX, satY),
                style = Stroke(width = if (isSelected) 2f else 1f)
            )

            // Pulse ring
            if (isSelected) {
                drawCircle(
                    color = satColor.copy(alpha = 0.3f),
                    radius = 20f,
                    center = Offset(satX, satY)
                )
            }

            // Central Satellite Dot
            drawCircle(
                color = satColor,
                radius = if (isSelected) 8f else 6f,
                center = Offset(satX, satY)
            )
            drawCircle(
                color = Color.White,
                radius = if (isSelected) 4f else 3f,
                center = Offset(satX, satY)
            )
        }
    }
}
