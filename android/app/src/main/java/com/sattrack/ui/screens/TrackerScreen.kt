package com.sattrack.ui.screens

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import com.sattrack.data.model.ObserverLocation
import com.sattrack.data.model.SatelliteState
import com.sattrack.ui.components.OrbitMapView
import com.sattrack.ui.components.TelemetryBottomSheet

@Composable
fun TrackerScreen(
    trackedStates: List<SatelliteState>,
    selectedId: Int,
    observer: ObserverLocation,
    onSelectSatellite: (Int) -> Unit
) {
    val activeState = trackedStates.find { it.id == selectedId } ?: trackedStates.firstOrNull()

    Box(modifier = Modifier.fillMaxSize()) {
        OrbitMapView(
            satellites = trackedStates,
            selectedId = selectedId,
            observer = observer,
            onSelectSatellite = onSelectSatellite,
            modifier = Modifier.fillMaxSize()
        )

        TelemetryBottomSheet(
            state = activeState,
            modifier = Modifier.align(Alignment.BottomCenter)
        )
    }
}
