package com.sattrack.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sattrack.ui.theme.*

@Composable
fun TopAppBar(
    onOpenSettings: () -> Unit
) {
    Surface(
        color = BgSurface,
        tonalElevation = 4.dp,
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .statusBarsPadding()
                .padding(horizontal = 16.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(36.dp)
                        .clip(RoundedCornerShape(10.dp))
                        .background(CyanAccent),
                    contentAlignment = Alignment.Center
                ) {
                    Text("🛰️", fontSize = 18.sp)
                }
                Spacer(modifier = Modifier.width(10.dp))
                Column {
                    Text(
                        text = "SatTrack Native",
                        style = MaterialTheme.typography.titleMedium,
                        color = TextMain
                    )
                    Text(
                        text = "SGP4 Orbit Propagation",
                        style = MaterialTheme.typography.bodyMedium,
                        color = TextMuted,
                        fontSize = 11.sp
                    )
                }
            }

            Row(verticalAlignment = Alignment.CenterVertically) {
                // Offline Ready badge
                Box(
                    modifier = Modifier
                        .clip(RoundedCornerShape(999.dp))
                        .background(EmeraldGlow)
                        .padding(horizontal = 8.dp, vertical = 4.dp)
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(
                            modifier = Modifier
                                .size(6.dp)
                                .clip(CircleShape)
                                .background(EmeraldAccent)
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = "Offline Engine",
                            color = EmeraldAccent,
                            fontSize = 11.sp,
                            fontWeight = androidx.compose.ui.text.font.FontWeight.SemiBold
                        )
                    }
                }

                Spacer(modifier = Modifier.width(8.dp))

                IconButton(
                    onClick = onOpenSettings,
                    modifier = Modifier.size(40.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.Settings,
                        contentDescription = "Settings",
                        tint = TextMain
                    )
                }
            }
        }
    }
}
