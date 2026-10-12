package com.sattrack.ui.components

import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.sattrack.ui.theme.*

data class NavDestination(
    val route: String,
    val icon: String,
    val label: String
)

@Composable
fun BottomNavigationBar(
    currentRoute: String,
    onNavigate: (String) -> Unit
) {
    val items = listOf(
        NavDestination("track", "📡", "Track"),
        NavDestination("globe", "🌐", "Globe"),
        NavDestination("catalog", "🔍", "Catalog"),
        NavDestination("passes", "⏱️", "Passes"),
        NavDestination("ai", "✨", "AI Assist")
    )

    NavigationBar(
        containerColor = BgSurface,
        tonalElevation = 8.dp,
        modifier = Modifier.navigationBarsPadding()
    ) {
        items.forEach { dest ->
            val isSelected = currentRoute == dest.route
            NavigationBarItem(
                selected = isSelected,
                onClick = { onNavigate(dest.route) },
                icon = {
                    Text(
                        text = dest.icon,
                        fontSize = if (isSelected) 22.sp else 18.sp
                    )
                },
                label = {
                    Text(
                        text = dest.label,
                        color = if (isSelected) CyanAccent else TextMuted,
                        fontSize = 11.sp
                    )
                },
                colors = NavigationBarItemDefaults.colors(
                    indicatorColor = CyanGlow,
                    selectedIconColor = CyanAccent,
                    unselectedIconColor = TextMuted
                )
            )
        }
    }
}
