# Add project specific ProGuard rules here.
-keepattributes *Annotation*
-keepattributes Signature
-keepattributes SourceFile,LineNumberTable

# OkHttp ProGuard Rules
-dontwarn okhttp3.**
-dontwarn okio.**
-keep class okhttp3.** { *; }

# Kotlin Coroutines
-keepnames class kotlinx.coroutines.internal.MainDispatcherFactory {}
-keepnames class kotlinx.coroutines.CoroutineExceptionHandler {}
