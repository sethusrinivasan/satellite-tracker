package com.sattrack

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import com.sattrack.data.repository.SatelliteRepository
import com.sattrack.data.repository.UserPreferencesRepository
import com.sattrack.ui.components.BottomNavigationBar
import com.sattrack.ui.components.TopAppBar
import com.sattrack.ui.screens.*
import com.sattrack.ui.theme.SatelliteTrackerTheme
import com.sattrack.ui.viewmodel.SatelliteViewModel

/**
 * Main Activity hosting the Jetpack Compose user interface for the native Satellite Tracker.
 * Configures edge-to-edge layout, dependency injection for repositories/viewmodel,
 * top/bottom navigation chrome, and screen routing.
 */
class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        val prefsRepo = UserPreferencesRepository(applicationContext)
        val satRepo = SatelliteRepository()

        setContent {
            SatelliteTrackerTheme {
                val viewModel: SatelliteViewModel = viewModel {
                    SatelliteViewModel(
                        repository = satRepo,
                        preferencesRepository = prefsRepo
                    )
                }

                val currentTab by viewModel.selectedTab.collectAsState()
                val trackedStates by viewModel.trackedStates.collectAsState()
                val selectedId by viewModel.selectedSatId.collectAsState()
                val observer by viewModel.observer.collectAsState()
                val passes by viewModel.passes.collectAsState()
                val satellites by viewModel.satellites.collectAsState()
                val trackedIds by viewModel.trackedIds.collectAsState()
                val searchQuery by viewModel.searchQuery.collectAsState()
                val selectedCategory by viewModel.selectedCategory.collectAsState()
                val isSyncing by viewModel.isSyncing.collectAsState()
                val chatMessages by viewModel.chatMessages.collectAsState()
                val showSettings by viewModel.showSettings.collectAsState()

                Scaffold(
                    topBar = {
                        TopAppBar(
                            onOpenSettings = { viewModel.toggleSettingsDialog(true) }
                        )
                    },
                    bottomBar = {
                        BottomNavigationBar(
                            currentRoute = currentTab,
                            onNavigate = { viewModel.selectTab(it) }
                        )
                    }
                ) { innerPadding ->
                    Box(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(innerPadding)
                    ) {
                        when (currentTab) {
                            "track" -> TrackerScreen(
                                trackedStates = trackedStates,
                                selectedId = selectedId,
                                observer = observer,
                                onSelectSatellite = { viewModel.selectSatellite(it) }
                            )

                            "globe" -> GlobeScreen(
                                trackedStates = trackedStates,
                                selectedId = selectedId
                            )

                            "catalog" -> CatalogScreen(
                                satellites = satellites,
                                trackedIds = trackedIds,
                                searchQuery = searchQuery,
                                selectedCategory = selectedCategory,
                                isSyncing = isSyncing,
                                onSearchChange = { viewModel.updateSearchQuery(it) },
                                onCategoryChange = { viewModel.selectCategory(it) },
                                onToggleTracking = { viewModel.toggleTracking(it) },
                                onSyncCelesTrak = { viewModel.syncCelesTrak() }
                            )

                            "passes" -> PassesScreen(
                                observer = observer,
                                passes = passes,
                                onRefreshGps = {
                                    // Refresh observer GPS coordinates
                                    viewModel.setObserverLocation(observer.latDeg, observer.lngDeg, observer.name)
                                }
                            )

                            "ai" -> AiDiscoveryScreen(
                                messages = chatMessages,
                                onSendMessage = { viewModel.sendAiPrompt(it) },
                                onTrackRecommendedSat = { satId ->
                                    viewModel.toggleTracking(satId)
                                    viewModel.selectSatellite(satId)
                                    viewModel.selectTab("track")
                                }
                            )
                        }

                        if (showSettings) {
                            SettingsDialog(
                                currentProvider = viewModel.getAiProvider(),
                                currentApiKey = viewModel.getAiApiKey(),
                                onDismiss = { viewModel.toggleSettingsDialog(false) },
                                onSave = { provider, key -> viewModel.saveSettings(provider, key) }
                            )
                        }
                    }
                }
            }
        }
    }
}
