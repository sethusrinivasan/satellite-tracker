package com.sattrack.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.sattrack.data.model.ObserverLocation
import com.sattrack.data.model.PassPrediction
import com.sattrack.data.model.SatelliteEntity
import com.sattrack.data.model.SatelliteState
import com.sattrack.data.remote.AiRemoteProvider
import com.sattrack.data.repository.SatelliteRepository
import com.sattrack.data.repository.UserPreferencesRepository
import com.sattrack.domain.ai.LocalQueryParser
import com.sattrack.domain.pass.PassPredictorEngine
import com.sattrack.domain.sgp4.Sgp4Engine
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

data class ChatMessage(
    val id: String = java.util.UUID.randomUUID().toString(),
    val isUser: Boolean,
    val text: String,
    val recommendedSatIds: List<Int> = emptyList()
)

class SatelliteViewModel(
    private val repository: SatelliteRepository = SatelliteRepository(),
    private val preferencesRepository: UserPreferencesRepository? = null,
    private val aiRemoteProvider: AiRemoteProvider = AiRemoteProvider()
) : ViewModel() {

    private val _selectedTab = MutableStateFlow("track")
    val selectedTab: StateFlow<String> = _selectedTab.asStateFlow()

    private val _trackedStates = MutableStateFlow<List<SatelliteState>>(emptyList())
    val trackedStates: StateFlow<List<SatelliteState>> = _trackedStates.asStateFlow()

    private val _selectedSatId = MutableStateFlow(25544)
    val selectedSatId: StateFlow<Int> = _selectedSatId.asStateFlow()

    private val _observer = MutableStateFlow(
        preferencesRepository?.observerLocation ?: ObserverLocation()
    )
    val observer: StateFlow<ObserverLocation> = _observer.asStateFlow()

    private val _passes = MutableStateFlow<List<PassPrediction>>(emptyList())
    val passes: StateFlow<List<PassPrediction>> = _passes.asStateFlow()

    private val _searchQuery = MutableStateFlow("")
    val searchQuery: StateFlow<String> = _searchQuery.asStateFlow()

    private val _selectedCategory = MutableStateFlow("all")
    val selectedCategory: StateFlow<String> = _selectedCategory.asStateFlow()

    private val _isSyncing = MutableStateFlow(false)
    val isSyncing: StateFlow<Boolean> = _isSyncing.asStateFlow()

    private val _chatMessages = MutableStateFlow<List<ChatMessage>>(
        listOf(
            ChatMessage(
                isUser = false,
                text = "Hello! I am your native Orbital Discovery Assistant. Ask queries about space stations, constellations, weather satellites, or orbital parameters."
            )
        )
    )
    val chatMessages: StateFlow<List<ChatMessage>> = _chatMessages.asStateFlow()

    private val _showSettings = MutableStateFlow(false)
    val showSettings: StateFlow<Boolean> = _showSettings.asStateFlow()

    val satellites: StateFlow<List<SatelliteEntity>> = repository.satellites
    val trackedIds: StateFlow<Set<Int>> = repository.trackedIds

    init {
        startSgp4Ticker()
        computePasses()
    }

    private fun startSgp4Ticker() {
        viewModelScope.launch(Dispatchers.Default) {
            while (isActive) {
                val now = System.currentTimeMillis()
                val tracked = repository.getTrackedSatellites()
                val states = tracked.map { Sgp4Engine.propagate(it, now) }
                _trackedStates.value = states
                delay(1500)
            }
        }
    }

    fun selectTab(tab: String) {
        _selectedTab.value = tab
        if (tab == "passes") {
            computePasses()
        }
    }

    fun selectSatellite(id: Int) {
        _selectedSatId.value = id
        computePasses()
    }

    fun toggleTracking(id: Int) {
        repository.toggleTracking(id)
    }

    fun updateSearchQuery(query: String) {
        _searchQuery.value = query
    }

    fun selectCategory(cat: String) {
        _selectedCategory.value = cat
    }

    fun syncCelesTrak() {
        viewModelScope.launch {
            _isSyncing.value = true
            try {
                repository.syncCelesTrakGroup("stations")
            } finally {
                _isSyncing.value = false
            }
        }
    }

    fun setObserverLocation(lat: Double, lng: Double, name: String) {
        val updated = ObserverLocation(latDeg = lat, lngDeg = lng, name = name)
        _observer.value = updated
        preferencesRepository?.observerLocation = updated
        computePasses()
    }

    fun computePasses() {
        viewModelScope.launch(Dispatchers.Default) {
            val all = repository.satellites.value
            val sat = all.find { it.id == _selectedSatId.value } ?: all.firstOrNull() ?: return@launch
            val result = PassPredictorEngine.predictPasses(sat, _observer.value)
            _passes.value = result
        }
    }

    fun sendAiPrompt(prompt: String) {
        val text = prompt.trim()
        if (text.isEmpty()) return

        val userMsg = ChatMessage(isUser = true, text = text)
        _chatMessages.value = _chatMessages.value + userMsg

        viewModelScope.launch {
            val provider = preferencesRepository?.aiProvider ?: "local"
            val key = preferencesRepository?.aiApiKey ?: ""

            if (provider != "local" && key.isNotEmpty()) {
                try {
                    val remoteResponse = aiRemoteProvider.query(provider, key, text)
                    val matchedIds = repository.satellites.value
                        .filter { remoteResponse.contains(it.name, ignoreCase = true) || remoteResponse.contains(it.id.toString()) }
                        .map { it.id }
                        .take(3)

                    _chatMessages.value = _chatMessages.value + ChatMessage(
                        isUser = false,
                        text = remoteResponse,
                        recommendedSatIds = matchedIds
                    )
                    return@launch
                } catch (e: Exception) {
                    // Fall back to local query engine
                }
            }

            // Local Query Engine
            val localResult = LocalQueryParser.parseQuery(text, repository.satellites.value)
            _chatMessages.value = _chatMessages.value + ChatMessage(
                isUser = false,
                text = localResult.text,
                recommendedSatIds = localResult.matchedSatellites.map { it.id }
            )
        }
    }

    fun toggleSettingsDialog(show: Boolean) {
        _showSettings.value = show
    }

    fun saveSettings(provider: String, apiKey: String) {
        preferencesRepository?.aiProvider = provider
        preferencesRepository?.aiApiKey = apiKey
        _showSettings.value = false
    }

    fun getAiProvider(): String = preferencesRepository?.aiProvider ?: "local"
    fun getAiApiKey(): String = preferencesRepository?.aiApiKey ?: ""
}
