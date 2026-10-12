package com.sattrack.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sattrack.data.model.SatelliteState
import com.sattrack.ui.components.Globe3DView
import com.sattrack.ui.components.TelemetryBottomSheet
import com.sattrack.ui.theme.*

@Composable
fun GlobeScreen(
    trackedStates: List<SatelliteState>,
    selectedId: Int
) {
    val activeState = trackedStates.find { it.id == selectedId } ?: trackedStates.firstOrNull()

    Box(modifier = Modifier.fillMaxSize()) {
        Globe3DView(
            satellites = trackedStates,
            selectedId = selectedId,
            modifier = Modifier.fillMaxSize()
        )

        // 3D HUD Badge at top
        Box(
            modifier = Modifier
                .align(Alignment.TopCenter)
                .padding(top = 16.dp)
                .clip(RoundedCornerShape(999.dp))
                .background(BgSurface.copy(alpha = 0.85f))
                .padding(horizontal = 14.dp, vertical = 6.dp)
        ) {
            Text(
                text = "🌐 3D Spatial Orbit Mode • Drag to Rotate",
                color = CyanAccent,
                fontSize = 12.sp,
                fontWeight = FontWeight.SemiBold
            )
        }

        TelemetryBottomSheet(
            state = activeState,
            modifier = Modifier.align(Alignment.BottomCenter)
        )
    }
}
