<p align="center">
  <img src="assets/hero.svg" width="100%" alt="Host Ubuntu estendido para um notebook Windows e um Galaxy A56 através de monitores virtuais no GNOME Wayland">
</p>

<h1 align="center">Monitores virtuais GNOME Wayland para o Sunshine</h1>

<p align="center">
  Transforme um notebook Windows e um celular Android em telas estendidas de verdade.<br>
  Um único desktop GNOME, streams independentes, taxas de atualização mistas.
</p>

<p align="center">
  <a href="https://github.com/lirenzzzin/gnome-wayland-virtual-monitors-sunshine/actions/workflows/ci.yml"><img alt="CI" src="https://img.shields.io/github/actions/workflow/status/lirenzzzin/gnome-wayland-virtual-monitors-sunshine/ci.yml?branch=main&amp;style=flat-square&amp;label=checks&amp;color=6EE7F2"></a>
  <img alt="GNOME 46" src="https://img.shields.io/badge/GNOME-46-4A86CF?style=flat-square">
  <img alt="Wayland" src="https://img.shields.io/badge/sess%C3%A3o-Wayland-F6C85F?style=flat-square">
  <a href="LICENSE"><img alt="GPL 3.0" src="https://img.shields.io/badge/licen%C3%A7a-GPL--3.0-A78BFA?style=flat-square"></a>
</p>

<p align="center">
  <a href="README.md">English</a> · <b>Português</b>
</p>

> [!WARNING]
> Esta é uma integração experimental com o GNOME/Mutter, validada em um único sistema GNOME 46 + NVIDIA. Usa interfaces D-Bus privadas e processos Sunshine isolados. Leia as [arestas conhecidas](#arestas-conhecidas) antes de instalar.

## O que você ganha

| Extensão real | Um stream por dispositivo | Refresh independente |
| --- | --- | --- |
| As janelas passam naturalmente para além da borda da tela física. Nada é espelhado. | Identidades Sunshine separadas capturam as saídas do notebook e do celular ao mesmo tempo. | A tela principal e o celular rodam a 120 Hz enquanto o notebook permanece a 60 Hz. |

O desktop validado é assim:

| Superfície | Modo | Posição no GNOME | Caminho do cliente |
| --- | ---: | --- | --- |
| Primária física | **1920×1080 · 120 Hz** | centro | local |
| Notebook Windows | **1366×768 · 60 Hz** | esquerda | Sunshine → Moonlight |
| Galaxy A56 | **2340×1080 · 120 Hz · ~175%** | centralizado abaixo | Sunshine → Moonlight Android |

Nos bastidores, um daemon de usuário pede ao Mutter saídas `RecordVirtual`, mantém vivos os nós PipeWire dessas saídas e aplica o layout estendido. O Sunshine captura cada saída pela sua própria sessão do XDG Portal.

## Início rápido

### 1. Instale as dependências do host

```bash
sudo apt update
sudo apt install \
  python3-gi \
  gir1.2-gstreamer-1.0 \
  gstreamer1.0-pipewire \
  gstreamer1.0-tools \
  pipewire-bin
```

Instale o [Sunshine](https://docs.lizardbyte.dev/projects/sunshine/latest/md_docs_2getting__started.html) no Ubuntu e o [Moonlight](https://moonlight-stream.org/) em cada cliente. Os arquivos de serviço fornecidos esperam o Sunshine nativo em `/usr/bin/sunshine`.

### 2. Clone e inspecione o host

```bash
git clone https://github.com/lirenzzzin/gnome-wayland-virtual-monitors-sunshine.git
cd gnome-wayland-virtual-monitors-sunshine
./scripts/doctor.sh
```

Um aviso sobre escala fracionária é esperado antes da instalação; o instalador pode habilitar o recurso necessário do Mutter.

### 3. Instale o serviço de usuário

```bash
./scripts/install-user.sh
${EDITOR:-nano} ~/.config/gnome-virtual-monitors/config.toml
PYTHONPATH="$HOME/.local/lib/gnome-wayland-virtual-monitors-sunshine" \
  python3 -m gnome_virtual_monitors \
  --config "$HOME/.config/gnome-virtual-monitors/config.toml" \
  --check-config
systemctl --user enable --now gnome-virtual-monitor.service
```

Antes de habilitar o serviço:

- defina o conector físico, largura, altura e refresh da sua tela principal;
- dê a cada monitor virtual um par largura/altura único; e
- lembre-se de que a v0.1 gerencia uma primária física mais as saídas virtuais configuradas.

O instalador fica dentro do seu diretório home. Ele não inicia um daemon root, não substitui um módulo de kernel, não sobrescreve uma configuração de monitor existente nem apaga recursos do Mutter não relacionados durante o rollback.

### 4. Conecte os clientes

Mantenha a instância normal do Sunshine para o notebook Windows. Instale a instância Android isolada de `experimental/`, selecione a saída ampla do celular no diálogo do Portal do GNOME e depois adicione `HOST_IP:48049` no Moonlight Android.

Para o Galaxy A56:

- ative **Tela → Suavidade de movimento → Adaptável**;
- escolha **2340×1080 a 120 FPS** no Moonlight;
- comece em torno de **28 Mbps**, H.264, frame pacing de menor latência; e
- use o touchscreen como trackpad para a saída não primária.

O passo a passo completo de pareamento, Portal, porta, H.264/NVENC, MediaCodec, Windows e Android está em [Configuração do Sunshine e Moonlight](docs/SUNSHINE.md).

## Um botão a evitar

> [!CAUTION]
> Não clique em **Parar de compartilhar** no indicador de status do GNOME (o monitor com uma seta) enquanto os displays virtuais estiverem ativos. O GNOME inclui ali as sessões de saída virtual do daemon; pará-las destrói as saídas e pode invalidar os tokens do Portal do Sunshine.

Se acontecer, pare as duas instâncias do Sunshine, reinicie o daemon de monitores virtuais, aguarde `Display layout applied` e então reinicie e reautorize apenas as instâncias que falharem. Os comandos exatos de recuperação estão em [Solução de problemas](docs/TROUBLESHOOTING.md).

## Arestas conhecidas

- Só GNOME/Mutter — isto não é um protocolo Wayland independente de compositor.
- O Mutter 46 pode corromper o cursor embutido em torno de 175% de escala de screencast. O fallback documentado mantém o tamanho da UI trocando um pouco de nitidez.
- Aplicativos XWayland podem ficar mais borrados sob escala fracionária.
- `Meta-0` e `Meta-1` são nomes temporários; o daemon mapeia os papéis por resolução única.
- Recriar saídas virtuais pode invalidar seleções salvas no Portal.
- Dois processos Sunshine isolam captura e estado, não a posse de teclado/mouse.
- Suspender/retomar e versões mais novas do GNOME ainda precisam de mais testes.

## Documentação

| Guia | Use quando… |
| --- | --- |
| [Escopo do projeto](docs/PROJECT_SCOPE.md) | você quer as promessas exatas e os não-objetivos |
| [Arquitetura](docs/ARCHITECTURE.md) | você quer entender Mutter, PipeWire, layout e readiness |
| [Sunshine + Moonlight](docs/SUNSHINE.md) | você está pareando Windows ou Android e ajustando 60/120 FPS |
| [Solução de problemas](docs/TROUBLESHOOTING.md) | Portal, cursor, seleção de saída ou FPS se comportam mal |
| [Testes](docs/TESTING.md) | você está validando uma máquina nova ou versão do GNOME |
| [Rollback](docs/ROLLBACK.md) | você quer remover o daemon sem apagar o estado do cliente |
| [Segurança](SECURITY.md) | você está revisando tokens, portas, criptografia ou confiança de entrada |
| [Trabalhos anteriores](PRIOR_ART.md) | você quer o trabalho upstream sobre o qual esta integração é construída |

<details>
<summary><strong>Stack validada</strong></summary>

- Zorin OS 18, baseado no Ubuntu 24.04
- GNOME Shell e Mutter 46.2 no Wayland
- NVIDIA GTX 1650, driver proprietário 595.71.05
- Sunshine 2026.516.143833 com captura via XDG Portal
- PipeWire 1.0.5 e GStreamer `pipewiresrc`
- Notebook Windows a 1366×768, 60 Hz
- Galaxy A56 deitado a 2340×1080, 120 Hz, escala GNOME de ~175%
- Moonlight Android com decodificação H.264 por hardware

</details>

## AI-friendly

Lendo isto com um assistente? Aponte qualquer modelo — ChatGPT, Claude, Gemini, Copilot ou um local — para [`docs/ai/context.md`](docs/ai/context.md) para que ele reconheça a arquitetura, a stack validada e as arestas antes de sugerir mudanças. Prompts prontos ficam em [`docs/ai/prompts.md`](docs/ai/prompts.md), e o [`AGENTS.md`](AGENTS.md) é o ponto de entrada compartilhado. O contexto é público, não está atrelado a nenhuma conta e não concede permissões automáticas — é apenas entendimento compartilhado para qualquer assistente que você usar.

## Créditos

Criado e mantido por **Lina**. Licenciado sob [GPL-3.0-or-later](LICENSE).

Este projeto é independente e não tem afiliação com GNOME, Sunshine, LizardByte, Moonlight, NVIDIA, Microsoft ou Samsung.
