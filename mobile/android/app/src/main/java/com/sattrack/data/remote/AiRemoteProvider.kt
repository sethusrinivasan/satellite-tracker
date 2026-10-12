package com.sattrack.data.remote

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.TimeUnit

class AiRemoteProvider {

    private val httpClient = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(25, TimeUnit.SECONDS)
        .build()

    suspend fun query(
        provider: String,
        apiKey: String,
        prompt: String
    ): String = withContext(Dispatchers.IO) {
        when (provider.lowercase()) {
            "gemini" -> queryGemini(apiKey, prompt)
            "openai" -> queryOpenAI(apiKey, prompt)
            "anthropic" -> queryAnthropic(apiKey, prompt)
            else -> throw IllegalArgumentException("Unsupported AI provider: $provider")
        }
    }

    private fun queryGemini(apiKey: String, prompt: String): String {
        val url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=$apiKey"
        val json = JSONObject().apply {
            put("contents", JSONArray().apply {
                put(JSONObject().apply {
                    put("parts", JSONArray().apply {
                        put(JSONObject().apply {
                            put("text", "You are an expert aerospace engineer and orbital tracker. Answer succinctly: $prompt")
                        })
                    })
                })
            })
        }

        val request = Request.Builder()
            .url(url)
            .post(json.toString().toRequestBody("application/json".toMediaType()))
            .build()

        httpClient.newCall(request).execute().use { response ->
            if (!response.isSuccessful) throw IOException("Gemini API returned ${response.code}: ${response.message}")
            val respBody = response.body?.string() ?: throw IOException("Empty response from Gemini")
            val root = JSONObject(respBody)
            return root.getJSONArray("candidates")
                .getJSONObject(0)
                .getJSONObject("content")
                .getJSONArray("parts")
                .getJSONObject(0)
                .getString("text")
        }
    }

    private fun queryOpenAI(apiKey: String, prompt: String): String {
        val url = "https://api.openai.com/v1/chat/completions"
        val json = JSONObject().apply {
            put("model", "gpt-4o-mini")
            put("messages", JSONArray().apply {
                put(JSONObject().apply {
                    put("role", "user")
                    put("content", prompt)
                })
            })
        }

        val request = Request.Builder()
            .url(url)
            .header("Authorization", "Bearer $apiKey")
            .post(json.toString().toRequestBody("application/json".toMediaType()))
            .build()

        httpClient.newCall(request).execute().use { response ->
            if (!response.isSuccessful) throw IOException("OpenAI API returned ${response.code}: ${response.message}")
            val respBody = response.body?.string() ?: throw IOException("Empty response from OpenAI")
            val root = JSONObject(respBody)
            return root.getJSONArray("choices")
                .getJSONObject(0)
                .getJSONObject("message")
                .getString("content")
        }
    }

    private fun queryAnthropic(apiKey: String, prompt: String): String {
        val url = "https://api.anthropic.com/v1/messages"
        val json = JSONObject().apply {
            put("model", "claude-3-haiku-20240307")
            put("max_tokens", 512)
            put("messages", JSONArray().apply {
                put(JSONObject().apply {
                    put("role", "user")
                    put("content", prompt)
                })
            })
        }

        val request = Request.Builder()
            .url(url)
            .header("x-api-key", apiKey)
            .header("anthropic-version", "2023-06-01")
            .post(json.toString().toRequestBody("application/json".toMediaType()))
            .build()

        httpClient.newCall(request).execute().use { response ->
            if (!response.isSuccessful) throw IOException("Anthropic API returned ${response.code}: ${response.message}")
            val respBody = response.body?.string() ?: throw IOException("Empty response from Anthropic")
            val root = JSONObject(respBody)
            return root.getJSONArray("content")
                .getJSONObject(0)
                .getString("text")
        }
    }
}
