# SpyderSec: Challenge — Tece a Teia, Decodifica a Verdade

Bora rapaziada!! SpyderSec é genuinamente uma das boxes mais criativas que já vi no VulnHub. Esqueça o SQLi ou brute-force usual. Esta encadeia extração de metadados EXIF, decodificação hex para ASCII, decriptação Base64, desempacotamento de eval JavaScript, análise de cookie Burp Suite, detecção de volume oculto TrueCrypt por esteganografia e montagem VeraCrypt, tudo para encontrar duas flags dentro de um volume oculto. É um puzzle de forense e stego disfarçado de boot2root. Nenhum shell necessário. O desafio recompensa paciência, curiosidade e recusa em pular etapas "chatas" como exiftool. Legitimamente uma das experiências CTF mais únicas disponíveis. Mano, top demais demais!

| Campo | Valor |
|---|---|
| **Nível** | Intermediário |
| **VM Alvo** | SpyderSec: Challenge |
| **VM Atacante** | Kali Linux 2024.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/spydersec-challenge,128/ |
| **Técnicas** | Enumeração de serviços de rede, análise de metadados EXIF com exiftool, decodificação hex para ASCII, decodificação Base64, desempacotamento eval JavaScript e análise de ofuscação, interceptação de cookie com Burp Suite e construção de URL, detecção de volume oculto TrueCrypt com tcsteg.py, montagem de volume oculto VeraCrypt |
| **CVEs** | CWE-312 (Armazenamento em Texto Claro: senha embutida em metadados EXIF), CWE-200 (Exposição de Informação: caminho interno divulgado via cookie de sessão), CWE-327 (Uso de Algoritmo Criptográfico Arriscado: volume oculto TrueCrypt) |
| **Grupos APT** | APT29 (Cozy Bear): usa técnicas esteganográficas para ocultar dados C2 em imagens; Lazarus Group: embute payloads e caminhos codificados em JavaScript ofuscado para comunicação C2 e staging de dados |

---

## Resumo do Ataque

```
nmap → porta 22 (SSH), porta 80 (HTTP)
  → wget Challenge.png do web root
  → exiftool Challenge.png → Comentário: string hex
  → hex → ASCII → Base64 → senha/dica decodificada
  → código-fonte da página: bloco JavaScript eval() ofuscado
  → desempacotamento JS eval → string hex → "alert('mulder.fbi')"
  → Burp Suite: interceptar requisição → cookie de sessão contém caminho URL
  → construir URL de download: http://alvo/<caminho>/mulder.fbi
  → file mulder.fbi → volume TrueCrypt
  → python tcsteg.py mulder.fbi → volume oculto detectado
  → VeraCrypt: montar volume oculto com senha do Passo 1
  → ls /media/veracrypt1/ → flag1.txt + flag2.txt
  → cat flags
```

---

## Metodologia

1. Descoberta de host e scan de portas: apenas SSH e HTTP
2. Baixar e analisar `Challenge.png` para metadados EXIF
3. Decodificar string hex do comentário EXIF: hex para ASCII para Base64
4. Desempacotar ofuscação JavaScript `eval()`: extrair string hex e decodificar para nome de arquivo
5. Interceptar cookie de sessão HTTP com Burp Suite para descobrir caminho de arquivo oculto
6. Baixar container TrueCrypt `mulder.fbi` da URL construída
7. Detectar volume esteganográfico oculto com `tcsteg.py`
8. Montar volume oculto com VeraCrypt e a senha do Passo 3
9. Ler ambas as flags do volume montado

---

## Passo 1 — Descoberta de Host e Scan de Portas

Identifique o alvo e enumere os serviços:

```bash
sudo netdiscover -i eth1 -r 192.168.1.0/24
# Alvo: 192.168.1.101

export TARGET=192.168.1.101
nmap -A $TARGET
```

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.x
80/tcp open  http    Apache httpd 2.4.x
```

Apenas duas portas. SSH e HTTP. Nenhum framework de aplicação web óbvio. A superfície de ataque é quase inteiramente forense.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Análise de Metadados EXIF

Baixe a imagem principal da web e analise seus metadados EXIF. Campos EXIF são frequentemente ignorados durante avaliações web, mas podem conter informações críticas colocadas por designers de desafios e, em engajamentos reais, acidentalmente por desenvolvedores ou câmeras.

```bash
mkdir /tmp/spydersec && cd /tmp/spydersec

wget http://$TARGET/Challenge.png
file Challenge.png
exiftool Challenge.png
```

O campo `Comment` do EXIF contém uma longa string hex:

```
Comment: 4d6f6c646572...  (longa string hex)
```

Decodifique o hex para ASCII:

```bash
exiftool Challenge.png | grep -i comment | awk -F': ' '{print $2}' | xxd -r -p
# Saída: uma string codificada em Base64
```

Decodifique o Base64:

```bash
exiftool Challenge.png | grep -i comment | awk -F': ' '{print $2}' | xxd -r -p | base64 -d
```

A saída final decodificada é a senha para o volume oculto TrueCrypt/VeraCrypt. Salve-a.

```bash
# Salvar para uso posterior
PASSWORD=$(exiftool Challenge.png | grep -i comment | awk -F': ' '{print $2}' | xxd -r -p | base64 -d)
echo "Senha: $PASSWORD"
```

**Nota real:** A extração de metadados EXIF é uma etapa padrão em investigações de forense digital. Em resposta a incidentes reais, dados EXIF em imagens exfiltradas por atores de ameaça revelaram coordenadas GPS, fingerprints de dispositivos e canais de comunicação C2 codificados. O APT29 usa campos EXIF de imagens para embutir dados de configuração codificados para implantes, tornando a análise EXIF essencial em investigações de malware.

**MITRE ATT&CK:** T1027 — Arquivos ou Informações Ofuscadas; T1552.001 — Credenciais em Arquivos (via EXIF)

---

## Passo 3 — Desempacotamento de JavaScript Eval

Inspecione o código-fonte da página web para JavaScript ofuscado:

```bash
curl -s http://$TARGET/ | grep -A 5 "eval("
```

A página inicial contém um bloco `eval(...)` empacotado, uma técnica comum de ofuscação JavaScript que usa codificação `p,a,c,k,e,d` ou similar:

```javascript
eval(function(p,a,c,k,e,d){...}(...))
```

**Para desempacotar manualmente:**

1. Copie todo o bloco `eval(...)`
2. Substitua `eval(` por `console.log(` (ou cole no console do navegador com o `eval` externo removido)
3. Ou use um desempacotador online (ex.: `https://beautifier.io/`)

**Alternativamente com Node.js:**

```bash
# Salve o bloco eval em um arquivo, substitua eval por console.log
node -e "$(cat eval_block.js | sed 's/^eval(/console.log(/')"
```

A saída desempacotada revela outra string hex. Decodifique-a:

```bash
echo "4d756c6465722e666269" | xxd -r -p
# Saída: mulder.fbi
```

O arquivo alvo é `mulder.fbi`.

**MITRE ATT&CK:** T1027 — Arquivos ou Informações Ofuscadas; T1027.010 — Ofuscação de Comando

---

## Passo 4 — Análise de Cookie e Construção de URL

O caminho do arquivo `mulder.fbi` não está diretamente acessível no web root. É divulgado via cookie de sessão. Use o Burp Suite para interceptar uma requisição ao alvo:

**Configurar Burp Suite:**

1. Configurar proxy do navegador: `127.0.0.1:8080`
2. Navegar para `http://$TARGET/`
3. Interceptar a requisição no Burp Suite Proxy

**Examine o cabeçalho Cookie:**

```
Cookie: <nome>=<caminho-codificado-em-URL>
```

Decodifique o valor do cookie em URL:

```bash
echo "<valor_cookie>" | python3 -c "import sys, urllib.parse; print(urllib.parse.unquote(sys.stdin.read().strip()))"
```

O cookie decodificado contém um caminho de diretório. Acrescente `mulder.fbi` para construir a URL de download:

```
http://192.168.1.101/<caminho>/mulder.fbi
```

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1539 — Roubar Cookie de Sessão Web (consciência defensiva)

---

## Passo 5 — Download e Identificação do Container TrueCrypt

Baixe o arquivo e identifique seu tipo:

```bash
cd /tmp/spydersec

curl -s -o mulder.fbi "http://$TARGET/<caminho>/mulder.fbi"
file mulder.fbi
# TrueCrypt volume
ls -lh mulder.fbi
```

O arquivo é identificado como um volume TrueCrypt. TrueCrypt foi descontinuado em 2014; o VeraCrypt é seu sucessor mantido e lê volumes TrueCrypt.

**MITRE ATT&CK:** T1074.001 — Dados Armazenados: Armazenamento de Dados Local (entendendo técnicas de ocultação)

---

## Passo 6 — Detecção de Volume Oculto com tcsteg.py

TrueCrypt (e VeraCrypt) suporta "volumes ocultos": um segundo volume criptografado plausivelmente negável oculto dentro do espaço livre de um volume externo. Uma ferramenta especializada, `tcsteg.py`, detecta a presença de volumes ocultos analisando padrões de entropia:

```bash
# Clonar se não disponível
git clone https://github.com/ligos/tcsteg.git
cd tcsteg

python tcsteg.py /tmp/spydersec/mulder.fbi
# Saída: "Hidden drive detected"
```

A presença de um volume oculto é confirmada. A senha do volume externo e a senha do volume oculto são diferentes.

**O que é um volume oculto TrueCrypt?** Quando alguém acessa o volume externo com a senha externa, vê conteúdo isca (ou nada). O volume oculto é invisível e não pode ser provado que existe. Agências de aplicação da lei e atores de ameaça usam essa técnica para negabilidade plausível. O conteúdo oculto só é acessível com a senha correta do volume oculto, que obtivemos dos metadados EXIF.

**MITRE ATT&CK:** T1027.004 — Arquivos Ofuscados (conceito análogo: oculto dentro do container)

---

## Passo 7 — Montagem do Volume Oculto VeraCrypt

Monte o volume oculto usando VeraCrypt com a senha recuperada no Passo 2:

**Método GUI:**

1. Abra o VeraCrypt
2. Clique em "Select File" e escolha `/tmp/spydersec/mulder.fbi`
3. Clique em "Mount"
4. Quando solicitada a senha, insira `$PASSWORD`
5. Tente montar com a senha oculta

**Método CLI:**

```bash
# Instalar VeraCrypt se não estiver presente
sudo apt-get install veracrypt

# Montar via CLI
veracrypt --text \
  --mount /tmp/spydersec/mulder.fbi \
  /media/veracrypt1 \
  --password "$PASSWORD" \
  --protect-hidden no
```

Após montar, navegue pelo volume:

```bash
ls -la /media/veracrypt1/
# flag1.txt  flag2.txt
```

**MITRE ATT&CK:** T1078 — Contas Válidas (usando credenciais descobertas para acessar dados protegidos)

---

## Passo 8 — Captura das Flags

Leia ambas as flags:

```bash
cat /media/veracrypt1/flag1.txt
cat /media/veracrypt1/flag2.txt
```

Desmonte quando terminar:

```bash
veracrypt --text --dismount /media/veracrypt1
```

(☞ᴥ❍ʋ) Ambas as flags capturadas. A teia da aranha foi desembaraçada. Caramba, que box incrível mano!

**MITRE ATT&CK:** T1005 — Dados do Sistema Local

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Usado Para |
|---|---|---|---|
| Senha (do EXIF) | (decodificada de hex→base64 no Comentário EXIF) | Metadados EXIF do Challenge.png | Senha do volume oculto VeraCrypt |
| Nome do arquivo alvo | `mulder.fbi` | Desempacotamento eval JS: decode hex | Construção da URL de download |
| Caminho de arquivo oculto | (do cookie de sessão decodificado em URL) | Interceptação de cookie Burp Suite | Construção da URL de download |
| Flag 1 | (varia) | /media/veracrypt1/flag1.txt | Prova CTF |
| Flag 2 | (varia) | /media/veracrypt1/flag2.txt | Prova CTF |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Conclusão Principal |
|---|---|---|---|
| 1 | Senha codificada em metadados EXIF | Campos EXIF são rotineiramente ignorados em avaliações de segurança web; atores de ameaça embutem dados secretos em campos EXIF para comunicação C2 | Sempre execute `exiftool` em imagens de fontes não confiáveis; remova EXIF antes de publicar imagens |
| 2 | Caminho interno divulgado via cookie de sessão | Valores de cookie contendo caminhos codificados em URL expõem estrutura interna de diretório | Conteúdo de cookie nunca deve revelar caminhos internos; use identificadores de sessão opacos |
| 3 | Ofuscação JavaScript oculta nome de arquivo crítico | Ofuscação não fornece segurança: qualquer código do lado do cliente é trivialmente reversível | Mova segredos para o lado do servidor; ofuscação não é criptografia |
| 4 | Volume oculto TrueCrypt fornece negabilidade plausível | Volumes ocultos TrueCrypt/VeraCrypt são usados por atores de ameaça para armazenamento secreto | Organizações devem testar volumes ocultos em investigações forenses; tcsteg.py e VeraCrypt são as ferramentas |
| 5 | Arquivo sensível servido de caminho web acessível | Arquivos container no web root podem ser baixados e analisados por qualquer visitante | Mantenha arquivos sensíveis fora do web root; use autenticação e URLs assinadas |

---

## MITRE ATT&CK Mapeamento

| Fase | Tática | Técnica | TTP ID |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Coleta | Coleta | Dados do Sistema Local | T1005 |
| Evasão de Defesa | Evasão | Arquivos ou Informações Ofuscadas | T1027 |
| Evasão de Defesa | Ofuscação de Comando | Ofuscação de Comando | T1027.010 |
| Acesso a Credenciais | Credenciais | Credenciais em Arquivos (EXIF) | T1552.001 |
| Exfiltração | Dados Armazenados | Armazenamento de Dados Local | T1074.001 |
| Acesso Inicial | Contas Válidas | Contas Válidas (VeraCrypt) | T1078 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Remover metadados EXIF antes de publicar imagens**: use `exiftool -all= imagem.png` para remover todos os dados EXIF antes de fazer upload para servidores web
2. **Remover caminhos internos dos cookies de sessão**: use identificadores de sessão opacos (ex.: UUID aleatório); nunca codifique caminhos do sistema de arquivos em cookies
3. **Mover dicas JavaScript ofuscadas para o lado do servidor**: toda lógica que revela caminhos ou nomes de arquivos deve estar no servidor, nunca no código do lado do cliente
4. **Mover arquivos sensíveis para fora do web root**: configurar Apache/Nginx para servir downloads apenas via endpoints autenticados
5. **Implementar autenticação de download**: usar URLs assinadas e com expiração para todos os downloads de arquivos

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Auditar todos os arquivos web-acessíveis para dados sensíveis |
| Proteger | Segurança de Dados | Remover EXIF antes de publicar; mover segredos para o servidor |
| Proteger | Controle de Acesso | Autenticar todos os endpoints de download de arquivos; URLs assinadas |
| Detectar | Anomalias e Eventos | Alertar sobre downloads em massa; monitorar anomalias de cookie |
| Responder | Planejamento de Resposta | Revogar tokens de sessão expostos; auditar logs de download |
| Recuperar | Planejamento de Recuperação | Mover arquivos sensíveis; regenerar chaves de assinatura de sessão |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| SC-28 | Proteção de Informações em Repouso | Criptografar arquivos sensíveis; remover EXIF antes de publicar |
| AC-3 | Controle de Acesso | Autenticar endpoints de download; restringir acesso a arquivos |
| SC-8 | Confidencialidade de Transmissão | Criptografar downloads via TLS; usar URLs assinadas |
| SI-12 | Gestão de Informações | Não embutir caminhos ou credenciais em valores de cookie |
| CM-7 | Menor Funcionalidade | Remover lacunas de remoção EXIF dos pipelines de implantação |

### CISA KEV

A ocultação de dados via esteganografia e metadados ofuscados se alinha com a orientação CISA sobre técnicas de ameaça interna e APT (AA21-321A) descrevendo métodos secretos de staging de dados usados antes da exfiltração.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Ativos (ASSET) | Gerenciar Inventário de Ativos TI | MIL2 |
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |
| Consciência Situacional (SITUATION) | Realizar Detecção de Eventos e Incidentes | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Endurecimento de Configuração de Aplicação (remover EXIF; mover segredos para o servidor; autenticar downloads)
- **D3-HBPI** — Integridade do Pipeline de Build (automatizar remoção EXIF no pipeline de implantação)
- **D3-SFA** — Análise de Recursos de Software (auditar JavaScript do lado do cliente para caminhos e credenciais embutidos)

---

## Pensamentos Finais

SpyderSec: Challenge é uma experiência incrível, véi. Sem CVEs, sem Metasploit, sem brute-force. Apenas camadas de codificação, análise de metadados e montagem de container criptográfico. Esta box demonstra que "hackear" frequentemente é menos sobre explorar código e mais sobre ler o que já está lá: em campos EXIF, em comentários JavaScript, em valores de cookie.

A corrente de esteganografia multicamadas (EXIF hex para Base64 para volume oculto VeraCrypt) é diretamente aplicável a investigações de forense digital. `tcsteg.py` e VeraCrypt são ferramentas reais usadas em investigações reais. Aprender a usá-las em um contexto CTF é desenvolvimento profissional genuíno.

Esta box merece seu lugar no nível "experiência única". Legitimamente uma das máquinas CTF mais criativas já feitas. Top demais, mano!

Thanks guys!! (❍ᴥ❍ʋ)
