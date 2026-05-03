import gender_guesser.detector as gender

d = gender.Detector()

def get_gender_from_name(name):
    if not name or not name.strip():
        return 'unknown'
    
    first_name = name.strip().split()[0]
    result = d.get_gender(first_name)

    if result in ['male', 'mostly_male']:
        return 'male'
    elif result in ['female', 'mostly_female']:
        return 'female'
    else:
        return 'unknown'