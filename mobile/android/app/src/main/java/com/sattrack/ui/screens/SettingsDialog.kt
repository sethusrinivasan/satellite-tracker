package com.sattrack.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import com.sattrack.ui.theme.*

@Composable
fun SettingsDialog(
    currentProvider: String,
    currentApiKey: String,
    onDismiss: () -> Unit,
    onSave: (provider: String, apiKey: String) -> Unit
) {
    var selectedProvider by remember { mutableStateOf(currentProvider) }
    var apiKeyInput by remember { mutableStateOf(currentApiKey) }

    Dialog(onDismissRequest = onDismiss) {
        Surface(
            color = BgSurface,
            shape = RoundedCornerShape(20.dp),
            tonalElevation = 8.dp,
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(
                modifier = Modifier
                    .padding(20.dp)
                    .fillMaxWidth()
            ) {
                Text(
                    text = "⚙️ App Settings & AI Vault",
                    style = MaterialTheme.typography.titleLarge,
                    color = TextMain
                )

                Spacer(modifier = Modifier.height(14.dp))

                Text(
                    text = "AI PROVIDER (OPTIONAL REMOTE ACCESS)",
                    style = MaterialTheme.typography.labelSmall,
                    color = TextMuted
                )

                Spacer(modifier = Modifier.height(6.dp))

                val providers = listOf(
                    "local" to "Local SGP4 Parser (100% Offline, Zero Keys)",
                    "gemini" to "Google Gemini (1.5 Flash / Pro)",
                    "openai" to "OpenAI (GPT-4o / GPT-4o-mini)",
                    "anthropic" to "Anthropic (Claude 3.5 Sonnet / Haiku)"
                )

                providers.forEach { (key, label) ->
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 4.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        RadioButton(
                            selected = selectedProvider == key,
                            onClick = { selectedProvider = key },
                            colors = RadioButtonDefaults.colors(selectedColor = CyanAccent)
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = label,
                            color = if (selectedProvider == key) CyanAccent else TextMain,
                            fontSize = 12.sp
                        )
                    }
                }

                if (selectedProvider != "local") {
                    Spacer(modifier = Modifier.height(10.dp))
                    Text(
                        text = "API KEY VAULT",
                        style = MaterialTheme.typography.labelSmall,
                        color = TextMuted
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    OutlinedTextField(
                        value = apiKeyInput,
                        onValueChange = { apiKeyInput = it },
                        placeholder = { Text("Enter personal API key…", color = TextDim, fontSize = 12.sp) },
                        visualTransformation = PasswordVisualTransformation(),
                        singleLine = true,
                        shape = RoundedCornerShape(12.dp),
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

                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "🔒 Stored strictly in local device SharedPreferences. Never uploaded to proxy servers.",
                        color = EmeraldAccent,
                        fontSize = 10.sp
                    )
                }

                Spacer(modifier = Modifier.height(16.dp))

                HorizontalDivider(color = BorderSubtle)

                Spacer(modifier = Modifier.height(10.dp))

                Text(
                    text = "Satellite TLE Tracker v1.0.0 (Native Android)\n100% On-Device SGP4 Engine • CycloneDX Certified",
                    color = TextDim,
                    fontSize = 11.sp,
                    lineHeight = 16.sp
                )

                Spacer(modifier = Modifier.height(16.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.End
                ) {
                    TextButton(onClick = onDismiss) {
                        Text("Cancel", color = TextMuted)
                    }
                    Spacer(modifier = Modifier.width(8.dp))
                    Button(
                        onClick = { onSave(selectedProvider, apiKeyInput.trim()) },
                        colors = ButtonDefaults.buttonColors(containerColor = CyanAccent),
                        shape = RoundedCornerShape(10.dp)
                    ) {
                        Text("Save Settings", color = BgVoid, fontWeight = FontWeight.Bold)
                    }
                }
            }
        }
    }
}
