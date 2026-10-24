# Majeirkn AI — protótipo Android local

Aplicativo Android em Kotlin com interface nativa e backend C++ via JNI usando `llama.cpp`.
Destinado inicialmente ao Samsung Galaxy M53 (8 GB RAM, ABI `arm64-v8a`).

## Estado do projeto — leia antes de compilar

Este é um **projeto-fonte inicial**, não um APK pronto nem um produto já testado no M53. O projeto inclui a interface Android e a integração nativa básica. O `llama.cpp` precisa ser obtido e compilado. A API C++ de `llama.cpp` pode mudar entre versões; se ocorrer erro de compilação, use uma revisão compatível e ajuste o JNI conforme os headers dessa revisão. O gerador foi atualizado para aplicar o formato de conversa Qwen2.5-Instruct e amostragem top-k/top-p/temperatura. Portanto, use o modelo Qwen2.5-Instruct indicado abaixo; outros modelos podem exigir outro template. O projeto ainda não oferece streaming, persistência de histórico nem cancelamento de geração. A API C++ muda entre versões do llama.cpp; valide a revisão usada e ajuste o JNI se necessário.

## Requisitos

- Android Studio recente
- Android SDK Platform 35
- Android NDK instalado pelo SDK Manager
- CMake 3.22.1
- JDK 17
- Espaço livre: vários GB para o modelo e ferramentas de compilação

## 1. Obter o código do motor

No computador, na pasta do projeto:

```bash
git clone https://github.com/ggml-org/llama.cpp app/src/main/cpp/llama.cpp
```

A estrutura deve conter:
`app/src/main/cpp/llama.cpp/CMakeLists.txt` e `app/src/main/cpp/llama.cpp/include/llama.h`.

## 2. Compilar automaticamente pelo GitHub Actions

Se você está usando apenas o celular, pode usar o navegador para criar um repositório GitHub, enviar estes arquivos e abrir a aba **Actions**. O workflow `.github/workflows/android-debug.yml` tenta compilar o APK e disponibilizá-lo como artefato. Execute **Build Android debug APK → Run workflow**. Se a compilação falhar por incompatibilidade da API C++ do `llama.cpp`, abra o log da etapa `Build debug APK` e use o erro para corrigir a versão do motor. Não publique chaves ou dados privados no repositório.

O workflow baixa a versão atual do `llama.cpp`, então uma mudança upstream pode quebrar o build; para builds reproduzíveis, fixe uma revisão conhecida após validar a compilação. A existência do workflow não significa que o APK já foi compilado.

## 3. Abrir e compilar

1. Abra a pasta `MajeirknAI` no Android Studio.
2. Instale Android SDK 35, NDK e CMake 3.22.1 pelo SDK Manager.
3. Aguarde o Gradle Sync.
4. Selecione um dispositivo Android ARM64 ou um emulador compatível.
5. Execute **Build > Build APK(s)**.

Para gerar um APK de depuração pelo terminal, primeiro gere o Gradle Wrapper (uma vez) com Gradle instalado:

```bash
gradle wrapper --gradle-version 8.9
./gradlew assembleDebug
```

No Windows, execute `gradle.bat wrapper --gradle-version 8.9` e depois `gradlew.bat assembleDebug`. O arquivo esperado será:
`app/build/outputs/apk/debug/app-debug.apk`

No Windows, use `gradlew.bat assembleDebug`.

## 4. Modelo GGUF

Modelo inicial recomendado: Qwen2.5-1.5B-Instruct, quantização `Q4_K_M`.
Página oficial do modelo:
https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF

Baixe o arquivo GGUF `Q4_K_M` para o computador ou telefone. No app, toque em **Selecionar modelo GGUF** e selecione o arquivo. A primeira cópia para o armazenamento privado pode demorar e ocupar espaço duplicado.

O tamanho exato depende do arquivo quantizado escolhido. Garanta espaço livre suficiente antes de copiar.

## Privacidade e rede

O código do aplicativo não faz requisições de rede e não declara permissão `INTERNET`. O modelo deve ser transferido manualmente. Depois de instalado o modelo, a inferência ocorre no dispositivo.

## Ajustes recomendados para o M53

- Comece com contexto 2048; aumente somente depois de medir memória.
- Feche aplicativos pesados antes de carregar o modelo.
- Use o telefone conectado à energia se a sessão for longa.
- Se o Android encerrar o processo por falta de memória, use um modelo menor ou quantização mais agressiva.

## Licenças

- Este projeto de exemplo: MIT (ver `LICENSE`).
- `llama.cpp`: licença do repositório upstream; confira antes de redistribuir.
- Pesos Qwen: Apache-2.0 conforme a página do modelo; confira os termos do arquivo escolhido.

## Limitações atuais

- Sem streaming de tokens.
- O histórico aparece na tela, mas não é salvo entre reinicializações nem incluído nas próximas inferências.
- O template Qwen2.5-Instruct é montado manualmente; use apenas modelos compatíveis com esse formato.
- A API C++ muda com o tempo; valide a revisão do llama.cpp usada.
- Não inclui APK pré-compilado. É necessário compilar e testar com Android Studio/NDK.


## Validação de build

Não foi possível executar uma compilação Android real neste ambiente porque não há Android SDK/NDK/Gradle Wrapper instalados. Assim, o ZIP é fonte atualizado, não um APK validado. Após abrir no Android Studio, execute Sync e Build; se surgir erro C++ de API, envie o texto completo do Build Output para alinhar o JNI à revisão de `llama.cpp` instalada.
