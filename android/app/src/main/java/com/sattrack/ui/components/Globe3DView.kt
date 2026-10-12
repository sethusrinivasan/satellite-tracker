package com.sattrack.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import com.sattrack.data.model.SatelliteState
import com.sattrack.ui.theme.*
import kotlin.math.*

@Composable
fun Globe3DView(
    satellites: List<SatelliteState>,
    selectedId: Int,
    modifier: Modifier = Modifier
) {
    // Rotation angles in radians
    var rotX by remember { mutableFloatStateOf(0.2f) }
    var rotY by remember { mutableFloatStateOf(0.0f) }

    Canvas(
        modifier = modifier
            .fillMaxSize()
            .pointerInput(Unit) {
                detectDragGestures { change, dragAmount ->
                    change.consume()
                    rotY += dragAmount.x * 0.008f
                    rotX = (rotX + dragAmount.y * 0.008f).coerceIn(-1.2f, 1.2f)
                }
            }
    ) {
        val cx = size.width / 2f
        val cy = size.height / 2f
        val globeR = min(size.width, size.height) * 0.32f

        // 1. Background Void
        drawRect(color = BgVoid)

        // 2. Atmospheric Outer Glow
        drawCircle(
            color = CyanAccent.copy(alpha = 0.12f),
            radius = globeR * 1.08f,
            center = Offset(cx, cy)
        )
        drawCircle(
            color = CyanAccent.copy(alpha = 0.06f),
            radius = globeR * 1.15f,
            center = Offset(cx, cy)
        )

        // 3. Earth Globe Sphere
        drawCircle(
            color = Color(0xFF0F2544),
            radius = globeR,
            center = Offset(cx, cy)
        )
        drawCircle(
            color = CyanAccent.copy(alpha = 0.45f),
            radius = globeR,
            center = Offset(cx, cy),
            style = Stroke(width = 2f)
        )

        // 4. Earth Coordinate Graticules (Parallels & Meridians projected on sphere)
        val cosRx = cos(rotX.toDouble()).toFloat()
        val sinRx = sin(rotX.toDouble()).toFloat()

        for (latDeg in -60..60 step 30) {
            val latRad = Math.toRadians(latDeg.toDouble())
            val rRing = globeR * cos(latRad).toFloat()
            val yRing = globeR * sin(latRad).toFloat()

            val ringPath = Path()
            var first = true
            for (step in 0..64) {
                val t = (step / 64.0) * 2.0 * Math.PI + rotY.toDouble()
                val x0 = rRing * cos(t).toFloat()
                val z0 = rRing * sin(t).toFloat()
                val y0 = yRing

                // Rotate around X
                val yRot = y0 * cosRx - z0 * sinRx
                val zRot = y0 * sinRx + z0 * cosRx

                if (zRot >= 0) { // Visible on front hemisphere
                    val px = cx + x0
                    val py = cy - yRot
                    if (first) {
                        ringPath.moveTo(px, py)
                        first = false
                    } else {
                        ringPath.lineTo(px, py)
                    }
                } else {
                    first = true
                }
            }
            drawPath(path = ringPath, color = Color(0x2E38BDF8), style = Stroke(width = 1f))
        }

        // 5. 3D Satellite Orbital Rings & Spacecraft Markers
        satellites.forEach { sat ->
            val isSelected = sat.id == selectedId
            val satColor = try {
                Color(android.graphics.Color.parseColor(sat.colorHex))
            } catch (_: Exception) {
                CyanAccent
            }

            val rOrbit = globeR * (1f + (sat.altKm.toFloat() / 6378.137f) * 0.85f).coerceIn(1.05f, 1.6f)
            val incRad = Math.toRadians(sat.inclinationDeg)

            // Draw inclined 3D orbit ring
            val orbitPath = Path()
            var firstPt = true
            for (step in 0..72) {
                val u = (step / 72.0) * 2.0 * Math.PI
                // In orbital plane
                val xOrb = (rOrbit * cos(u)).toFloat()
                val yOrb = (rOrbit * sin(u) * sin(incRad)).toFloat()
                val zOrb = (rOrbit * sin(u) * cos(incRad)).toFloat()

                // Apply globe rotation (rotY and rotX)
                val cosRy = cos(rotY.toDouble()).toFloat()
                val sinRy = sin(rotY.toDouble()).toFloat()
                val x1 = xOrb * cosRy + zOrb * sinRy
                val z1 = -xOrb * sinRy + zOrb * cosRy

                val y2 = yOrb * cosRx - z1 * sinRx
                val z2 = yOrb * sinRx + z1 * cosRx

                val px = cx + x1
                val py = cy - y2

                if (firstPt) {
                    orbitPath.moveTo(px, py)
                    firstPt = false
                } else {
                    orbitPath.lineTo(px, py)
                }
            }
            drawPath(
                path = orbitPath,
                color = satColor.copy(alpha = if (isSelected) 0.6f else 0.25f),
                style = Stroke(width = if (isSelected) 2f else 1f)
            )

            // Calculate current 3D position of satellite
            val satLatRad = Math.toRadians(sat.latDeg)
            val satLngRad = Math.toRadians(sat.lngDeg) + rotY.toDouble()

            val xSat0 = (rOrbit * cos(satLatRad) * sin(satLngRad)).toFloat()
            val ySat0 = (rOrbit * sin(satLatRad)).toFloat()
            val zSat0 = (rOrbit * cos(satLatRad) * cos(satLngRad)).toFloat()

            val ySatRot = ySat0 * cosRx - zSat0 * sinRx
            val zSatRot = ySat0 * sinRx + zSat0 * cosRx
            val xSatRot = xSat0

            val px = cx + xSatRot
            val py = cy - ySatRot

            val isVisibleFront = zSatRot >= -globeR * 0.3f
            if (isVisibleFront) {
                // Glow & marker
                if (isSelected) {
                    drawCircle(
                        color = satColor.copy(alpha = 0.35f),
                        radius = 16f,
                        center = Offset(px, py)
                    )
                }
                drawCircle(
                    color = satColor,
                    radius = if (isSelected) 7f else 5f,
                    center = Offset(px, py)
                )
                drawCircle(
                    color = Color.White,
                    radius = if (isSelected) 3.5f else 2.5f,
                    center = Offset(px, py)
                )
            }
        }
    }
}
