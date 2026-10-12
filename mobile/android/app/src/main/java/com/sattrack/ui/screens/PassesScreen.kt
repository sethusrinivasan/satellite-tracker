package com.sattrack.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sattrack.data.model.ObserverLocation
import com.sattrack.data.model.PassPrediction
import com.sattrack.domain.pass.PassPredictorEngine
import com.sattrack.ui.theme.*
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun PassesScreen(
    observer: ObserverLocation,
    passes: List<PassPrediction>,
    onRefreshGps: () -> Unit
) {
    val timeFormat = SimpleDateFormat("HH:mm", Locale.getDefault())
    val now = System.currentTimeMillis()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BgVoid)
            .padding(horizontal = 16.dp)
    ) {
        Spacer(modifier = Modifier.height(12.dp))

        // Observer Location Card
        Surface(
            color = BgSurface,
            shape = RoundedCornerShape(16.dp),
            tonalElevation = 4.dp,
            modifier = Modifier.fillMaxWidth()
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(14.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Column {
                    Text(
                        text = "OBSERVER LOCATION",
                        style = MaterialTheme.typography.labelSmall,
                        color = TextMuted
                    )
                    Spacer(modifier = Modifier.height(2.dp))
                    Text(
                        text = "${observer.latDeg}° N, ${observer.lngDeg}° E",
                        fontFamily = FontFamily.Monospace,
                        color = TextMain,
                        fontWeight = FontWeight.Bold,
                        fontSize = 13.sp
                    )
                }

                Button(
                    onClick = onRefreshGps,
                    colors = ButtonDefaults.buttonColors(containerColor = EmeraldAccent.copy(alpha = 0.25f)),
                    shape = RoundedCornerShape(10.dp),
                    contentPadding = PaddingValues(horizontal = 10.dp, vertical = 6.dp),
                    modifier = Modifier.height(34.dp)
                ) {
                    Text("📍 GPS", color = EmeraldAccent, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                }
            }
        }

        Spacer(modifier = Modifier.height(14.dp))

        Text(
            text = "Upcoming Visible Passes (Next 24h)",
            style = MaterialTheme.typography.titleMedium,
            color = TextMain
        )

        Spacer(modifier = Modifier.height(8.dp))

        if (passes.isEmpty()) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 40.dp),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    text = "🛰️ No visible passes above 10° elevation detected in the next 24 hours.",
                    color = TextMuted,
                    fontSize = 13.sp,
                    textAlign = androidx.compose.ui.text.style.TextAlign.Center
                )
            }
        } else {
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                verticalArrangement = Arrangement.spacedBy(10.dp),
                contentPadding = PaddingValues(bottom = 24.dp)
            ) {
                items(passes) { pass ->
                    val diffMs = pass.aosTimeMs - now
                    val hrsIn = diffMs / 3600000L
                    val minsIn = (diffMs % 3600000L) / 60000L
                    val countdown = if (diffMs > 0) {
                        if (hrsIn > 0) "In ${hrsIn}h ${minsIn}m" else "In ${minsIn} mins"
                    } else "Happening now"

                    val durMin = pass.durationSec / 60
                    val durSec = pass.durationSec % 60

                    Surface(
                        color = BgCard,
                        shape = RoundedCornerShape(14.dp),
                        tonalElevation = 2.dp,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(modifier = Modifier.padding(14.dp)) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                Column {
                                    Text(
                                        text = pass.satName,
                                        style = MaterialTheme.typography.titleMedium,
                                        color = TextMain
                                    )
                                    Text(
                                        text = "${timeFormat.format(Date(pass.aosTimeMs))} ($countdown)",
                                        color = CyanAccent,
                                        fontWeight = FontWeight.SemiBold,
                                        fontSize = 12.sp
                                    )
                                }

                                val badgeColor = when (pass.quality) {
                                    "EXCELLENT" -> EmeraldAccent
                                    "GOOD" -> CyanAccent
                                    else -> AmberAccent
                                }

                                Box(
                                    modifier = Modifier
                                        .clip(RoundedCornerShape(999.dp))
                                        .background(badgeColor.copy(alpha = 0.2f))
                                        .padding(horizontal = 10.dp, vertical = 4.dp)
                                ) {
                                    Text(
                                        text = pass.quality,
                                        color = badgeColor,
                                        fontWeight = FontWeight.Bold,
                                        fontSize = 11.sp
                                    )
                                }
                            }

                            Spacer(modifier = Modifier.height(8.dp))

                            Text(
                                text = "Max Elevation: ${pass.maxElevDeg.toInt()}° (Peak at ${timeFormat.format(Date(pass.maxElevTimeMs))}) • Duration: ${durMin}m ${durSec}s",
                                color = TextMuted,
                                fontSize = 12.sp
                            )

                            Spacer(modifier = Modifier.height(10.dp))

                            // Sky Compass Radar Row
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clip(RoundedCornerShape(10.dp))
                                    .background(BgVoid)
                                    .padding(horizontal = 12.dp, vertical = 8.dp),
                                horizontalArrangement = Arrangement.SpaceAround
                            ) {
                                Text(
                                    text = "↗ Rise: ${PassPredictorEngine.azimuthToCompassDirection(pass.aosAzimuthDeg)}",
                                    color = TextMuted,
                                    fontSize = 11.sp
                                )
                                Text(
                                    text = "▲ Peak: ${pass.maxElevDeg.toInt()}° ${PassPredictorEngine.azimuthToCompassDirection(pass.maxAzimuthDeg)}",
                                    color = CyanAccent,
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 11.sp
                                )
                                Text(
                                    text = "↘ Set: ${PassPredictorEngine.azimuthToCompassDirection(pass.losAzimuthDeg)}",
                                    color = TextMuted,
                                    fontSize = 11.sp
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}
