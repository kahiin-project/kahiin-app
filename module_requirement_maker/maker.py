import pkg_resources
import requests
from collections import OrderedDict

def get_package_info(package_name, processed=None, results=None, depth=0):
    """
    Récupère récursivement les informations sur un package et ses dépendances.
    
    Args:
        package_name (str): Nom du package à analyser
        processed (set): Ensemble des packages déjà traités
        results (OrderedDict): Dictionnaire ordonné stockant les résultats
        depth (int): Profondeur de récursion actuelle
    
    Returns:
        OrderedDict: Dictionnaire des résultats {package_name: (github_url, tarball_url)}
    """
    if processed is None:
        processed = set()
    if results is None:
        results = OrderedDict()
    
    # Évite les doublons
    if package_name in processed:
        return results
    
    processed.add(package_name)
    print(f"{' ' * depth}Analyse de {package_name}...")
    
    try:
        # Requête PyPI
        pypi_url = f"https://pypi.org/pypi/{package_name}/json"
        response = requests.get(pypi_url)
        package_data = response.json()
        
        # Trouve l'URL GitHub
        github_url = None
        project_urls = package_data.get('info', {}).get('project_urls', {})
        
        for url in project_urls.values():
            if url and 'github.com' in url.lower():
                github_url = url.split('/tree/')[0].split('/issues/')[0].split('#')[0].rstrip('/')
                break
        
        if not github_url:
            home_page = package_data.get('info', {}).get('home_page')
            if home_page and 'github.com' in home_page.lower():
                github_url = home_page.split('/tree/')[0].split('/issues/')[0].split('#')[0].rstrip('/')
        
        # Trouve l'URL du tarball
        tarball_url = None
        releases = package_data.get('releases', {})
        latest_version = package_data['info']['version']
        
        if latest_version in releases:
            for file_info in releases[latest_version]:
                if file_info['filename'].endswith('.tar.gz'):
                    tarball_url = file_info['url']
                    break
        
        # Stocke les résultats
        results[package_name] = (github_url, tarball_url)
        
        # Analyse récursive des dépendances
        try:
            package = pkg_resources.working_set.by_key[package_name]
            for req in package.requires():
                dep_name = req.project_name
                get_package_info(dep_name, processed, results, depth + 1)
        except Exception as e:
            print(f"{' ' * depth}Erreur avec les dépendances de {package_name}: {str(e)}")
            
    except Exception as e:
        print(f"{' ' * depth}Erreur avec {package_name}: {str(e)}")
        results[package_name] = (None, None)
    
    return results

def write_results(results, base_name):
    """
    Écrit les résultats dans les fichiers de sortie.
    
    Args:
        results (OrderedDict): Résultats à écrire
        base_name (str): Nom de base pour les fichiers de sortie
    """
    # Écrit les dépendances
    with open(f"{base_name}_dependencies.txt", 'w', encoding='utf-8') as f:
        for package in results.keys():
            f.write(f"{package}\n")
    
    # Écrit les tarballs (sans doublons)
    with open(f"{base_name}_tarballs.txt", 'w', encoding='utf-8') as f:
        tarballs = set(tarball for _, tarball in results.values() if tarball is not None)
        f.write(','.join(tarballs))

def main():
    import sys
    if len(sys.argv) < 2:
        print("Usage: python script.py package_name")
        sys.exit(1)
    
    package_name = sys.argv[1]
    print(f"Analyse de {package_name} et ses dépendances...")
    
    # Obtient toutes les informations
    results = get_package_info(package_name)
    
    # Écrit les résultats
    write_results(results, package_name)
    print(f"Analyse terminée. Résultats écrits dans {package_name}_dependencies.txt et {package_name}_tarballs.txt")

if __name__ == "__main__":
    main()