#include <jni.h>
#include <string>
#include <mutex>
#include <vector>
#include <algorithm>
#include "llama.h"

static llama_model *g_model = nullptr;
static llama_context *g_ctx = nullptr;
static std::mutex g_mutex;

static std::string fromJString(JNIEnv *env, jstring value) {
    const char *chars = env->GetStringUTFChars(value, nullptr);
    std::string result = chars ? chars : "";
    if (chars) env->ReleaseStringUTFChars(value, chars);
    return result;
}
static jstring toJString(JNIEnv *env, const std::string &s) {
    return env->NewStringUTF(s.c_str());
}

extern "C" JNIEXPORT jstring JNICALL
Java_com_majeirkn_ai_MainActivity_nativeLoadModel(JNIEnv *env, jobject, jstring path, jint contextSize) {
    std::lock_guard<std::mutex> lock(g_mutex);
    if (g_ctx) { llama_free(g_ctx); g_ctx = nullptr; }
    if (g_model) { llama_model_free(g_model); g_model = nullptr; }
    llama_backend_init();
    llama_model_params mp = llama_model_default_params();
    mp.n_gpu_layers = 0; // CPU primeiro: compatibilidade e consumo previsível.
    std::string modelPath = fromJString(env, path);
    g_model = llama_model_load_from_file(modelPath.c_str(), mp);
    if (!g_model) return toJString(env, "Falha ao abrir o modelo. Verifique se o arquivo GGUF é válido.");
    llama_context_params cp = llama_context_default_params();
    cp.n_ctx = static_cast<uint32_t>(contextSize);
    cp.n_batch = 256;
    g_ctx = llama_init_from_model(g_model, cp);
    if (!g_ctx) {
        llama_model_free(g_model); g_model = nullptr;
        return toJString(env, "Não foi possível iniciar o contexto. Tente um modelo menor.");
    }
    return toJString(env, "OK — modelo carregado localmente.");
}

extern "C" JNIEXPORT jstring JNICALL
Java_com_majeirkn_ai_MainActivity_nativeGenerate(JNIEnv *env, jobject, jstring promptJ, jint maxTokens) {
    std::lock_guard<std::mutex> lock(g_mutex);
    if (!g_model || !g_ctx) return toJString(env, "Nenhum modelo carregado.");

    const std::string userText = fromJString(env, promptJ);
    // Template de conversa do Qwen2.5-Instruct. Este protótipo é direcionado ao modelo Qwen.
    const std::string prompt =
        "<|im_start|>system\n"
        "Você é a Majeirkn AI, uma assistente útil que responde em português brasileiro. "
        "Se não souber algo, diga que não sabe.\n<|im_end|>\n"
        "<|im_start|>user\n" + userText +
        "\n<|im_end|>\n<|im_start|>assistant\n";

    const llama_vocab *vocab = llama_model_get_vocab(g_model);
    const int needed = llama_tokenize(vocab, prompt.c_str(), (int)prompt.size(), nullptr, 0, true, true);
    if (needed >= 0) return toJString(env, "Falha ao calcular os tokens do prompt.");
    std::vector<llama_token> tokens((size_t)-needed);
    const int tokenCount = llama_tokenize(vocab, prompt.c_str(), (int)prompt.size(), tokens.data(), (int)tokens.size(), true, true);
    if (tokenCount < 0) return toJString(env, "Erro ao tokenizar a mensagem.");
    tokens.resize(tokenCount);

    llama_memory_clear(llama_get_memory(g_ctx), true);
    llama_batch batch = llama_batch_get_one(tokens.data(), (int)tokens.size());
    if (llama_decode(g_ctx, batch) != 0) return toJString(env, "Erro ao processar o prompt. Tente uma mensagem menor.");

    llama_sampler *sampler = llama_sampler_chain_init(llama_sampler_chain_default_params());
    if (!sampler) return toJString(env, "Não foi possível inicializar o gerador.");
    llama_sampler_chain_add(sampler, llama_sampler_init_top_k(40));
    llama_sampler_chain_add(sampler, llama_sampler_init_top_p(0.90f, 1));
    llama_sampler_chain_add(sampler, llama_sampler_init_temp(0.70f));
    llama_sampler_chain_add(sampler, llama_sampler_init_dist(1234));

    std::string output;
    const int limit = std::max(1, (int)maxTokens);
    for (int i = 0; i < limit; ++i) {
        llama_token token = llama_sampler_sample(sampler, g_ctx, -1);
        if (llama_vocab_is_eog(vocab, token)) break;
        llama_sampler_accept(sampler, token);
        char piece[512];
        int n = llama_token_to_piece(vocab, token, piece, sizeof(piece), 0, true);
        if (n > 0) output.append(piece, (size_t)n);
        batch = llama_batch_get_one(&token, 1);
        if (llama_decode(g_ctx, batch) != 0) break;
    }
    llama_sampler_free(sampler);
    return toJString(env, output.empty() ? "O modelo não gerou texto. Tente outra mensagem." : output);
}

extern "C" JNIEXPORT void JNICALL
Java_com_majeirkn_ai_MainActivity_nativeRelease(JNIEnv *, jobject) {
    std::lock_guard<std::mutex> lock(g_mutex);
    if (g_ctx) { llama_free(g_ctx); g_ctx = nullptr; }
    if (g_model) { llama_model_free(g_model); g_model = nullptr; }
    llama_backend_free();
}
