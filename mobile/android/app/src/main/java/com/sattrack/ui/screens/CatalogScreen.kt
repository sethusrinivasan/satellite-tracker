package com.sattrack.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sattrack.data.model.SatelliteEntity
import com.sattrack.ui.theme.*

@Composable
fun CatalogScreen(
    satellites: List<SatelliteEntity>,
    trackedIds: Set<Int>,
    searchQuery: String,
    selectedCategory: String,
    isSyncing: Boolean,
    onSearchChange: (String) -> Unit,
    onCategoryChange: (String) -> Unit,
    onToggleTracking: (Int) -> Unit,
    onSyncCelesTrak: () -> Unit
) {
    val categories = listOf(
        "all" to "All",
        "stations" to "🛰️ Stations",
        "science" to "🔭 Science",
        "earth" to "🌍 Earth Obs",
        "weather" to "⛅ Weather",
        "gps" to "🧭 GPS/Nav",
        "starlink" to "📡 Starlink",
        "brightest" to "✨ Brightest"
    )

    val filtered = satellites.filter { sat ->
        val matchesCat = selectedCategory == "all" || sat.category.equals(selectedCategory, ignoreCase = true)
        val q = searchQuery.trim().lowercase()
        val matchesQuery = q.isEmpty() ||
                sat.name.lowercase().contains(q) ||
                sat.id.toString().contains(q) ||
                sat.orbitType.lowercase().contains(q)
        matchesCat && matchesQuery
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BgVoid)
            .padding(horizontal = 16.dp)
    ) {
        Spacer(modifier = Modifier.height(12.dp))

        // Search Input
        OutlinedTextField(
            value = searchQuery,
            onValueChange = onSearchChange,
            placeholder = { Text("Search by name, NORAD ID…", color = TextDim, fontSize = 14.sp) },
            leadingIcon = { Icon(Icons.Default.Search, contentDescription = null, tint = TextMuted) },
            singleLine = true,
            shape = RoundedCornerShape(14.dp),
            colors = OutlinedTextFieldDefaults.colors(
                focusedContainerColor = BgCard,
                unfocusedContainerColor = BgCard,
                focusedBorderColor = CyanAccent,
                unfocusedBorderColor = BorderSubtle,
                focusedTextColor = TextMain,
                unfocusedTextColor = TextMain
            ),
            modifier = Modifier.fillMaxWidth()
        )

        Spacer(modifier = Modifier.height(10.dp))

        // Category Chips Row
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            categories.forEach { (catKey, catLabel) ->
                val isSelected = selectedCategory == catKey
                FilterChip(
                    selected = isSelected,
                    onClick = { onCategoryChange(catKey) },
                    label = { Text(catLabel, fontSize = 12.sp) },
                    colors = FilterChipDefaults.filterChipColors(
                        selectedContainerColor = CyanAccent.copy(alpha = 0.2f),
                        selectedLabelColor = CyanAccent,
                        containerColor = BgCard,
                        labelColor = TextMuted
                    ),
                    border = FilterChipDefaults.filterChipBorder(
                        enabled = true,
                        selected = isSelected,
                        borderColor = if (isSelected) CyanAccent else BorderSubtle
                    )
                )
            }
        }

        Spacer(modifier = Modifier.height(10.dp))

        // CelesTrak Sync Bar
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(12.dp))
                .background(BgCard)
                .padding(horizontal = 12.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(
                text = "${filtered.size} Spacecraft Primed",
                color = TextMuted,
                fontSize = 12.sp
            )

            Button(
                onClick = onSyncCelesTrak,
                enabled = !isSyncing,
                colors = ButtonDefaults.buttonColors(containerColor = CyanAccent.copy(alpha = 0.25f)),
                contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp),
                modifier = Modifier.height(32.dp)
            ) {
                Icon(
                    imageVector = Icons.Default.Refresh,
                    contentDescription = null,
                    tint = CyanAccent,
                    modifier = Modifier.size(14.dp)
                )
                Spacer(modifier = Modifier.width(4.dp))
                Text(
                    text = if (isSyncing) "Syncing…" else "Sync CelesTrak",
                    color = CyanAccent,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.SemiBold
                )
            }
        }

        Spacer(modifier = Modifier.height(8.dp))

        // Satellite List
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            verticalArrangement = Arrangement.spacedBy(8.dp),
            contentPadding = PaddingValues(bottom = 24.dp)
        ) {
            items(filtered, key = { it.id }) { sat ->
                val isTracked = trackedIds.contains(sat.id)
                Surface(
                    color = BgCard,
                    shape = RoundedCornerShape(14.dp),
                    tonalElevation = 2.dp,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(14.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = sat.name,
                                style = MaterialTheme.typography.titleMedium,
                                color = TextMain
                            )
                            Spacer(modifier = Modifier.height(4.dp))
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Box(
                                    modifier = Modifier
                                        .clip(RoundedCornerShape(4.dp))
                                        .background(CyanAccent.copy(alpha = 0.15f))
                                        .padding(horizontal = 6.dp, vertical = 2.dp)
                                ) {
                                    Text(
                                        text = sat.orbitType,
                                        color = CyanAccent,
                                        fontSize = 10.sp,
                                        fontWeight = FontWeight.Bold
                                    )
                                }
                                Spacer(modifier = Modifier.width(8.dp))
                                Text(
                                    text = "NORAD ${sat.id} • ${sat.altitudeKm.toInt()} km",
                                    fontFamily = FontFamily.Monospace,
                                    color = TextMuted,
                                    fontSize = 11.sp
                                )
                            }
                        }

                        Button(
                            onClick = { onToggleTracking(sat.id) },
                            colors = ButtonDefaults.buttonColors(
                                containerColor = if (isTracked) EmeraldAccent.copy(alpha = 0.25f) else CyanAccent.copy(alpha = 0.15f)
                            ),
                            shape = RoundedCornerShape(10.dp),
                            contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp),
                            modifier = Modifier.height(34.dp)
                        ) {
                            Text(
                                text = if (isTracked) "✓ Tracked" else "+ Track",
                                color = if (isTracked) EmeraldAccent else CyanAccent,
                                fontSize = 12.sp,
                                fontWeight = FontWeight.SemiBold
                            )
                        }
                    }
                }
            }
        }
    }
}
