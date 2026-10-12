package com.sattrack.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable

private val DarkColorScheme = darkColorScheme(
    primary = CyanAccent,
    secondary = VioletAccent,
    tertiary = EmeraldAccent,
    background = BgVoid,
    surface = BgSurface,
    surfaceVariant = BgCard,
    onPrimary = BgVoid,
    onSecondary = TextMain,
    onTertiary = BgVoid,
    onBackground = TextMain,
    onSurface = TextMain,
    onSurfaceVariant = TextMuted,
    outline = BorderSubtle
)

@Composable
fun SatelliteTrackerTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = DarkColorScheme,
        typography = Typography,
        content = content
    )
}
